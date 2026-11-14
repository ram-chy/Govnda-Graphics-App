"""Database health and integrity diagnostics.

The diagnostics are read-only with one deliberate exception: the write check
opens a transaction with ``BEGIN IMMEDIATE`` and immediately rolls it back to
prove the file accepts writes. No table or row is modified. A health check never
deletes, recreates, or repairs a database.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import cast

from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.database.base import APPLICATION_ID
from app.infrastructure.database.engine import Database
from app.infrastructure.database.errors import (
    DatabaseFailureKind,
    classify_database_error,
    user_message_for,
)
from app.infrastructure.database.migrations import (
    MigrationManager,
    MigrationState,
    MigrationStatus,
)


class DatabaseHealthStatus(StrEnum):
    HEALTHY = "healthy"
    MISSING_DATABASE = "missing_database"
    UNAVAILABLE_PATH = "unavailable_path"
    PERMISSION_DENIED = "permission_denied"
    CORRUPT = "corrupt"
    LOCKED = "locked"
    WRONG_DATABASE = "wrong_database"
    FOREIGN_KEYS_DISABLED = "foreign_keys_disabled"
    INTEGRITY_ERROR = "integrity_error"
    MIGRATION_REQUIRED = "migration_required"
    MIGRATION_FAILED = "migration_failed"
    UNKNOWN_ERROR = "unknown_error"

    @property
    def healthy(self) -> bool:
        return self is DatabaseHealthStatus.HEALTHY


@dataclass(frozen=True, slots=True)
class IntegrityCheckResult:
    name: str
    ok: bool
    messages: tuple[str, ...] = ()

    @property
    def summary(self) -> str:
        return "ok" if self.ok else "; ".join(self.messages) or "failed"


@dataclass(frozen=True, slots=True)
class DatabaseFileInfo:
    path: Path
    exists: bool
    size_bytes: int | None = None
    wal_exists: bool = False
    wal_size_bytes: int | None = None
    shm_exists: bool = False
    shm_size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class DatabaseHealthReport:
    status: DatabaseHealthStatus
    message: str
    checks: Mapping[str, str] = field(default_factory=dict)
    file_info: DatabaseFileInfo | None = None
    sqlite_version: str | None = None
    application_id: int | None = None
    user_version: int | None = None
    migration: MigrationStatus | None = None

    @property
    def healthy(self) -> bool:
        return self.status.healthy

    @property
    def failure_kind(self) -> str:
        return self.status.value


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _file_info(database: Database) -> DatabaseFileInfo:
    config = database.config
    return DatabaseFileInfo(
        path=config.path,
        exists=config.path.exists(),
        size_bytes=_safe_size(config.path),
        wal_exists=config.wal_path.exists(),
        wal_size_bytes=_safe_size(config.wal_path),
        shm_exists=config.shm_path.exists(),
        shm_size_bytes=_safe_size(config.shm_path),
    )


def _integrity_rows(connection: object, pragma: str) -> IntegrityCheckResult:
    rows = connection.exec_driver_sql(pragma).fetchall()  # type: ignore[attr-defined]
    messages = tuple(str(row[0]) for row in rows if row and row[0] is not None)
    ok = bool(messages) and all(message.lower() == "ok" for message in messages)
    return IntegrityCheckResult(name=pragma, ok=ok, messages=messages)


class DatabaseDiagnostics:
    """Diagnostics for one :class:`Database` instance."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def quick_check(self) -> IntegrityCheckResult:
        try:
            with self._database.engine.connect() as connection:
                return _integrity_rows(connection, "PRAGMA quick_check")
        except (SQLAlchemyError, sqlite3.Error, OSError) as exc:
            return IntegrityCheckResult("PRAGMA quick_check", False, (str(exc),))

    def integrity_check(self) -> IntegrityCheckResult:
        try:
            with self._database.engine.connect() as connection:
                return _integrity_rows(connection, "PRAGMA integrity_check")
        except (SQLAlchemyError, sqlite3.Error, OSError) as exc:
            return IntegrityCheckResult("PRAGMA integrity_check", False, (str(exc),))

    def foreign_key_check(self) -> IntegrityCheckResult:
        try:
            with self._database.engine.connect() as connection:
                rows = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        except (SQLAlchemyError, sqlite3.Error, OSError) as exc:
            return IntegrityCheckResult("PRAGMA foreign_key_check", False, (str(exc),))
        messages = tuple(",".join(str(value) for value in row) for row in rows)
        return IntegrityCheckResult(
            name="PRAGMA foreign_key_check",
            ok=not messages,
            messages=messages,
        )

    def check(self, *, full: bool = False) -> DatabaseHealthReport:
        """Return a complete health report. Never raises for database failures.

        Args:
            full: Also run the expensive ``PRAGMA integrity_check``. Intended for
                maintenance and support, not every startup.
        """
        config = self._database.config
        file_info = _file_info(self._database)
        checks: dict[str, str] = {}

        # Path checks come first so a missing drive is reported without opening
        # anything and without creating a file.
        anchor = config.path.anchor
        if anchor and not Path(anchor).exists():
            checks["path"] = f"drive unavailable: {anchor}"
            return self._report(
                DatabaseHealthStatus.UNAVAILABLE_PATH,
                f"The configured drive is not available ({anchor}).",
                checks,
                file_info,
            )
        if not config.parent.exists():
            checks["path"] = f"parent folder missing: {config.parent}"
            return self._report(
                DatabaseHealthStatus.UNAVAILABLE_PATH,
                f"The configured database folder does not exist ({config.parent}).",
                checks,
                file_info,
            )
        if not config.parent.is_dir():
            checks["path"] = f"parent is not a directory: {config.parent}"
            return self._report(
                DatabaseHealthStatus.UNAVAILABLE_PATH,
                f"The configured database folder is not a directory ({config.parent}).",
                checks,
            )
        if not config.path.exists():
            checks["file"] = "missing"
            return self._report(
                DatabaseHealthStatus.MISSING_DATABASE,
                f"The database file does not exist ({config.path}).",
                checks,
                file_info,
            )
        if not config.path.is_file():
            checks["file"] = "not a regular file"
            return self._report(
                DatabaseHealthStatus.UNAVAILABLE_PATH,
                f"The configured database path is not a file ({config.path}).",
                checks,
                file_info,
            )

        checks["file"] = "exists"
        application_id: int | None = None
        user_version: int | None = None
        sqlite_version: str | None = None
        migration: MigrationStatus | None = None

        try:
            with self._database.engine.connect() as connection:
                checks["connection"] = "ok"
                application_id = _scalar_int(
                    connection.exec_driver_sql("PRAGMA application_id").scalar()
                )
                user_version = _scalar_int(
                    connection.exec_driver_sql("PRAGMA user_version").scalar()
                )
                sqlite_version = str(
                    connection.exec_driver_sql("SELECT sqlite_version()").scalar_one()
                )
                foreign_keys = _scalar_int(
                    connection.exec_driver_sql("PRAGMA foreign_keys").scalar()
                )
        except (SQLAlchemyError, sqlite3.Error, OSError) as exc:
            kind = classify_database_error(exc)
            checks["connection"] = f"failed: {kind}"
            status = {
                "locked": DatabaseHealthStatus.LOCKED,
                "corrupt": DatabaseHealthStatus.CORRUPT,
                "permission": DatabaseHealthStatus.PERMISSION_DENIED,
                "unavailable": DatabaseHealthStatus.UNAVAILABLE_PATH,
            }.get(kind, DatabaseHealthStatus.UNKNOWN_ERROR)
            return self._report(
                status,
                user_message_for(kind, config.path),
                checks,
                file_info,
            )

        if foreign_keys != 1:
            checks["foreign_keys"] = "disabled"
            return self._report(
                DatabaseHealthStatus.FOREIGN_KEYS_DISABLED,
                "SQLite foreign-key enforcement is not enabled on this connection.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
            )
        checks["foreign_keys"] = "ok"

        if application_id not in (0, APPLICATION_ID):
            checks["application_id"] = f"unexpected: {application_id}"
            return self._report(
                DatabaseHealthStatus.WRONG_DATABASE,
                "The file is not a Gobindas Graphics database.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
            )
        checks["application_id"] = "ok"

        quick = self.quick_check()
        checks["quick_check"] = quick.summary
        if not quick.ok:
            return self._report(
                DatabaseHealthStatus.CORRUPT,
                "The database failed SQLite quick_check and may be damaged.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
            )

        foreign_key_result = self.foreign_key_check()
        checks["foreign_key_check"] = foreign_key_result.summary
        if not foreign_key_result.ok:
            return self._report(
                DatabaseHealthStatus.INTEGRITY_ERROR,
                "The database contains rows that violate foreign-key constraints.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
            )

        if full:
            integrity = self.integrity_check()
            checks["integrity_check"] = integrity.summary
            if not integrity.ok:
                return self._report(
                    DatabaseHealthStatus.CORRUPT,
                    "The database failed the full SQLite integrity_check.",
                    checks,
                    file_info,
                    sqlite_version=sqlite_version,
                    application_id=application_id,
                    user_version=user_version,
                )

        write_status = self._check_write_capability()
        checks["read_write"] = write_status[0]
        if write_status[0] != "ok":
            status = {
                "locked": DatabaseHealthStatus.LOCKED,
                "permission": DatabaseHealthStatus.PERMISSION_DENIED,
                "unavailable": DatabaseHealthStatus.UNAVAILABLE_PATH,
            }.get(write_status[0], DatabaseHealthStatus.UNKNOWN_ERROR)
            return self._report(
                status,
                user_message_for(cast(DatabaseFailureKind, write_status[0]), config.path),
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
            )

        try:
            migration = MigrationManager(self._database).status()
        except Exception as exc:  # noqa: BLE001 - health must report, not raise
            checks["migration"] = f"failed: {exc}"
            return self._report(
                DatabaseHealthStatus.MIGRATION_FAILED,
                "The database schema revision could not be read.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
            )

        checks["migration"] = migration.state.value
        if migration.state in (
            MigrationState.NOT_INITIALIZED,
            MigrationState.UPGRADE_REQUIRED,
        ):
            return self._report(
                DatabaseHealthStatus.MIGRATION_REQUIRED,
                "The database schema must be migrated before the application can use it.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
                migration=migration,
            )
        if migration.state in (
            MigrationState.NEWER_SCHEMA,
            MigrationState.UNKNOWN_REVISION,
        ):
            return self._report(
                DatabaseHealthStatus.MIGRATION_FAILED,
                "The database schema is newer than this application understands.",
                checks,
                file_info,
                sqlite_version=sqlite_version,
                application_id=application_id,
                user_version=user_version,
                migration=migration,
            )

        return self._report(
            DatabaseHealthStatus.HEALTHY,
            "The database is healthy.",
            checks,
            file_info,
            sqlite_version=sqlite_version,
            application_id=application_id,
            user_version=user_version,
            migration=migration,
        )

    def _check_write_capability(self) -> tuple[str, str | None]:
        """Take and release a write lock without modifying any table or row."""
        raw = None
        try:
            raw = self._database.engine.raw_connection()
            cursor = raw.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute("ROLLBACK")
            finally:
                cursor.close()
            return "ok", None
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            kind = classify_database_error(exc)
            return kind, str(exc)
        finally:
            if raw is not None:
                raw.close()

    @staticmethod
    def _report(
        status: DatabaseHealthStatus,
        message: str,
        checks: dict[str, str],
        file_info: DatabaseFileInfo | None = None,
        *,
        sqlite_version: str | None = None,
        application_id: int | None = None,
        user_version: int | None = None,
        migration: MigrationStatus | None = None,
    ) -> DatabaseHealthReport:
        return DatabaseHealthReport(
            status=status,
            message=message,
            checks=dict(checks),
            file_info=file_info,
            sqlite_version=sqlite_version,
            application_id=application_id,
            user_version=user_version,
            migration=migration,
        )


def _scalar_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


__all__ = [
    "DatabaseDiagnostics",
    "DatabaseFileInfo",
    "DatabaseHealthReport",
    "DatabaseHealthStatus",
    "IntegrityCheckResult",
]
