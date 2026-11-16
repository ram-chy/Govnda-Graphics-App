"""SQLite Online Backup API snapshot and independent verification.

The live database is never copied as a file. A read-only connection is made to
the source and Python's ``sqlite3.Connection.backup`` copies a consistent
snapshot page by page (including WAL content). The temporary destination is
then reopened independently, checked with ``quick_check``, ``integrity_check``,
``foreign_key_check``, and inspected for identity and schema revision.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core import constants
from app.core.exceptions import BackupError, BackupVerificationError
from app.infrastructure.backup.hashing import sha256_file
from app.infrastructure.database.base import APPLICATION_ID

logger = logging.getLogger(__name__)

_BACKUP_PAGES_PER_STEP = 256
_UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DatabaseVerification:
    """Read-only facts and check results for one SQLite file."""

    path: Path
    size_bytes: int
    application_id: int | None
    user_version: int | None
    schema_revision: str | None
    page_count: int | None
    quick_check: tuple[str, ...]
    integrity_check: tuple[str, ...]
    foreign_key_check: tuple[str, ...]
    checks: dict[str, str] = field(default_factory=dict)

    @property
    def quick_ok(self) -> bool:
        return bool(self.quick_check) and all(item.lower() == "ok" for item in self.quick_check)

    @property
    def integrity_ok(self) -> bool:
        # A light preflight deliberately skips the full integrity scan. "not run"
        # is not a failure; any real check result must be "ok".
        if self.integrity_check == (_UNAVAILABLE,):
            return False
        if self.integrity_check == ("not run",):
            return True
        return bool(self.integrity_check) and all(
            item.lower() == "ok" for item in self.integrity_check
        )

    @property
    def foreign_key_ok(self) -> bool:
        return not self.foreign_key_check

    @property
    def identity_ok(self) -> bool:
        return self.application_id == APPLICATION_ID

    @property
    def ok(self) -> bool:
        return (
            self.size_bytes > 0
            and self.quick_ok
            and self.integrity_ok
            and self.foreign_key_ok
            and self.identity_ok
            and self.schema_revision is not None
        )

    @property
    def failure_summary(self) -> str:
        problems: list[str] = []
        if self.size_bytes <= 0:
            problems.append("the file is empty")
        if not self.quick_ok:
            problems.append(f"quick_check: {'; '.join(self.quick_check) or 'failed'}")
        if not self.integrity_ok:
            problems.append(f"integrity_check: {'; '.join(self.integrity_check) or 'failed'}")
        if not self.foreign_key_ok:
            problems.append(f"foreign_key_check: {'; '.join(self.foreign_key_check)}")
        if not self.identity_ok:
            problems.append(f"application_id is {self.application_id!r}")
        if self.schema_revision is None:
            problems.append("the schema revision could not be read")
        return "; ".join(problems) or "unknown verification failure"


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    """Statistics from a completed Online Backup API snapshot."""

    source_path: Path
    destination_path: Path
    source_bytes: int
    backup_bytes: int
    pages_copied: int
    duration_ms: int

    @property
    def sha256(self) -> str:
        return sha256_file(self.destination_path)


ProgressCallback = Any  # Callable[[int, str], None]


def read_schema_revision(connection: sqlite3.Connection) -> str | None:
    """Read the Alembic revision without importing Alembic.

    A database that has no ``alembic_version`` table or an empty version table is
    uninitialized and returns ``None``.
    """
    try:
        row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    except sqlite3.Error:
        return None
    if row is None or row[0] is None:
        return None
    text = str(row[0]).strip()
    return text or None


def read_database_revision(path: Path) -> str | None:
    """Open a database read-only and return its schema revision."""
    connection: sqlite3.Connection | None = None
    try:
        connection = _open_readonly(path)
        connection.execute("PRAGMA busy_timeout = 5000")
        return read_schema_revision(connection)
    except (sqlite3.Error, OSError):
        return None
    finally:
        if connection is not None:
            connection.close()


def verify_database_file(
    path: Path,
    *,
    full: bool = True,
    expected_application_id: int = APPLICATION_ID,
) -> DatabaseVerification:
    """Inspect a SQLite file read-only and return every safety check.

    No exception is raised for a corrupt or unreadable database: the result
    carries the failure so callers can display it. A missing file is reported as
    an empty file with unavailable checks.
    """
    target = Path(path)
    try:
        size = target.stat().st_size
    except OSError:
        size = 0

    checks: dict[str, str] = {"path": str(target)}
    if size <= 0:
        checks["file"] = "missing or empty"
        return DatabaseVerification(
            path=target,
            size_bytes=0,
            application_id=None,
            user_version=None,
            schema_revision=None,
            page_count=None,
            quick_check=(),
            integrity_check=(),
            foreign_key_check=(),
            checks=checks,
        )

    connection: sqlite3.Connection | None = None
    try:
        connection = _open_readonly(target)
        connection.execute("PRAGMA busy_timeout = 5000")
        checks["connection"] = "ok"

        quick = _pragma_messages(connection, "PRAGMA quick_check")
        checks["quick_check"] = "ok" if _all_ok(quick) else "; ".join(quick)
        integrity = (
            _pragma_messages(connection, "PRAGMA integrity_check")
            if full
            else ("not run",)
        )
        checks["integrity_check"] = (
            "ok" if _all_ok(integrity) else "; ".join(integrity)
        )
        foreign_key_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
        foreign_keys = tuple(
            ",".join(str(value) for value in row) for row in foreign_key_rows if row
        )
        checks["foreign_key_check"] = "ok" if not foreign_keys else "; ".join(foreign_keys)

        application_id = _scalar_int(connection, "PRAGMA application_id")
        user_version = _scalar_int(connection, "PRAGMA user_version")
        page_count = _scalar_int(connection, "PRAGMA page_count")
        revision = read_schema_revision(connection)
        checks["application_id"] = (
            "ok" if application_id == expected_application_id else f"unexpected: {application_id}"
        )
        checks["schema_revision"] = revision or "unavailable"
    except sqlite3.Error as exc:
        logger.info("SQLite verification failed for %s: %s", target, exc)
        checks["connection"] = f"failed: {exc}"
        return DatabaseVerification(
            path=target,
            size_bytes=size,
            application_id=None,
            user_version=None,
            schema_revision=None,
            page_count=None,
            quick_check=(str(exc),),
            integrity_check=(),
            foreign_key_check=(),
            checks=checks,
        )
    finally:
        if connection is not None:
            connection.close()

    return DatabaseVerification(
        path=target,
        size_bytes=size,
        application_id=application_id,
        user_version=user_version,
        schema_revision=revision,
        page_count=page_count,
        quick_check=quick,
        integrity_check=integrity,
        foreign_key_check=foreign_keys,
        checks=checks,
    )


def verify_writable(path: Path) -> tuple[bool, str]:
    """Prove the file accepts a write transaction without changing any row."""
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(str(Path(path)), timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("ROLLBACK")
        return True, "ok"
    except (sqlite3.Error, OSError) as exc:
        return False, str(exc)
    finally:
        if connection is not None:
            connection.close()


def create_snapshot(
    source_path: Path,
    destination_path: Path,
    *,
    progress: ProgressCallback | None = None,
) -> SnapshotResult:
    """Copy a consistent snapshot with the SQLite Online Backup API.

    ``destination_path`` must not exist. The temporary file is created in the
    destination directory so a later publish can use an atomic rename on the
    same volume.
    """
    source = Path(source_path)
    destination = Path(destination_path)
    if not source.is_file():
        raise BackupError(
            f"backup source does not exist: {source}",
            user_message=f"The database file does not exist ({source}).",
        )
    if source.stat().st_size <= 0:
        raise BackupError(
            f"backup source is empty: {source}",
            user_message="The database file is empty and cannot be backed up safely.",
        )
    if destination.exists():
        raise BackupError(
            f"backup destination already exists: {destination}",
            user_message="A backup file with that name already exists. Nothing was overwritten.",
        )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError(
            f"backup destination folder could not be created: {destination.parent}: {exc}",
            user_message=(
                f"The backup folder could not be created ({destination.parent}). Check the "
                "drive and its permissions."
            ),
        ) from exc

    started = time.monotonic()
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None
    created = False
    completed = False
    try:
        source_connection = _open_readonly(source)
        source_connection.execute("PRAGMA busy_timeout = 5000")
        destination_connection = sqlite3.connect(str(destination), timeout=5.0)
        created = True
        destination_connection.execute("PRAGMA busy_timeout = 5000")
        destination_connection.execute("PRAGMA synchronous = FULL")

        pages_copied = 0

        def _report(status: int, remaining: int, total: int) -> None:
            nonlocal pages_copied
            pages_copied = total - remaining
            if progress is not None:
                percent = 100 if total <= 0 else int((pages_copied * 100) / total)
                progress(percent, f"Copying database pages ({pages_copied}/{total})")
            if status == sqlite3.SQLITE_BUSY and progress is not None:
                progress(0, "Waiting for an active database writer")

        if progress is not None:
            progress(0, "Starting a consistent SQLite snapshot")
        source_connection.backup(
            destination_connection,
            pages=_BACKUP_PAGES_PER_STEP,
            progress=_report,
            sleep=0.05,
        )
        # The backup inherits the source header. Force a single-file journal mode
        # so verification and future restore never depend on sidecar files.
        try:
            destination_connection.execute("PRAGMA journal_mode = DELETE")
        except sqlite3.Error:
            logger.debug("Could not switch backup journal mode for %s", destination, exc_info=True)
        destination_connection.execute("PRAGMA synchronous = FULL")
        destination_connection.commit()
        completed = True
    except (sqlite3.Error, OSError) as exc:
        raise BackupError(
            f"SQLite Online Backup API failed for {source}: {exc}",
            user_message=(
                "The database backup could not be created. The live database was not "
                "modified and no backup was published. See the log for details."
            ),
        ) from exc
    finally:
        if destination_connection is not None:
            destination_connection.close()
        if source_connection is not None:
            source_connection.close()
        if created and not completed:
            destination.unlink(missing_ok=True)

    try:
        fsync_file(destination)
        backup_size = destination.stat().st_size
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise BackupError(
            f"backup temporary file could not be finalized: {destination}: {exc}",
            user_message=(
                "The backup file could not be written completely. No backup was published."
            ),
        ) from exc

    duration_ms = int((time.monotonic() - started) * 1000)
    if progress is not None:
        progress(100, "Snapshot complete")

    return SnapshotResult(
        source_path=source,
        destination_path=destination,
        source_bytes=source.stat().st_size,
        backup_bytes=backup_size,
        pages_copied=pages_copied,
        duration_ms=duration_ms,
    )


def verify_snapshot(path: Path) -> DatabaseVerification:
    """Verify a published or temporary backup and raise on any failure."""
    result = verify_database_file(path, full=True)
    if not result.ok:
        raise BackupVerificationError(
            f"backup verification failed for {path}: {result.failure_summary}",
            user_message=(
                "The backup did not pass verification and was not published: "
                f"{result.failure_summary}."
            ),
        )
    return result


def fsync_file(path: Path) -> None:
    """Flush a file to durable storage where the platform supports it.

    Windows rejects ``fsync`` on a read-only handle, so open the file writable.
    The handle is closed immediately and no content is modified.
    """
    descriptor = os.open(str(Path(path)), os.O_RDWR)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_directory(path: Path) -> None:
    """Best-effort directory flush (Windows does not permit opening a directory)."""
    try:
        descriptor = os.open(str(Path(path)), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        logger.debug("Directory fsync is not supported for %s", path)
    finally:
        os.close(descriptor)


def clean_stale_temporary_files(
    directory: Path,
    *,
    older_than_seconds: int = constants.STALE_TEMP_AGE_SECONDS,
    now_timestamp: float | None = None,
) -> tuple[Path, ...]:
    """Remove only this application's abandoned ``.tmp`` publish files.

    The age guard is deliberately conservative and does not apply to locks: a
    lock is reclaimed only after its owning process is proven dead.
    """
    folder = Path(directory)
    if not folder.is_dir():
        return ()
    cutoff = (time.time() if now_timestamp is None else now_timestamp) - older_than_seconds
    removed: list[Path] = []
    try:
        entries = list(folder.iterdir())
    except OSError:
        return ()
    for entry in entries:
        if not entry.name.startswith(".") or not entry.name.endswith(constants.BACKUP_TEMP_SUFFIX):
            continue
        try:
            if not entry.is_file():
                continue
            if entry.stat().st_mtime > cutoff:
                continue
            entry.unlink()
            removed.append(entry)
        except OSError:
            logger.warning("Stale backup temporary file could not be removed: %s", entry)
    if removed:
        logger.info("Removed %d stale backup temporary file(s) from %s", len(removed), folder)
    return tuple(removed)


def _open_readonly(path: Path) -> sqlite3.Connection:
    """Open read-only through a URI, falling back to query-only when needed."""
    uri = f"{Path(path).resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        connection.execute("PRAGMA query_only = ON")
        return connection
    except sqlite3.Error:
        logger.debug("Read-only SQLite URI failed for %s; retrying query_only", path)
    connection = sqlite3.connect(str(Path(path)), timeout=5.0)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _pragma_messages(connection: sqlite3.Connection, pragma: str) -> tuple[str, ...]:
    rows = connection.execute(pragma).fetchall()
    return tuple(str(row[0]) for row in rows if row and row[0] is not None)


def _all_ok(messages: tuple[str, ...]) -> bool:
    return bool(messages) and all(message.lower() == "ok" for message in messages)


def _scalar_int(connection: sqlite3.Connection, pragma: str) -> int | None:
    try:
        value = connection.execute(pragma).fetchone()
    except sqlite3.Error:
        return None
    if not value or value[0] is None:
        return None
    try:
        return int(value[0])
    except (TypeError, ValueError):
        return None


__all__ = [
    "DatabaseVerification",
    "SnapshotResult",
    "clean_stale_temporary_files",
    "create_snapshot",
    "fsync_directory",
    "fsync_file",
    "read_schema_revision",
    "verify_database_file",
    "verify_snapshot",
    "verify_writable",
]
