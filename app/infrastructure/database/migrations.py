"""Programmatic Alembic migration control.

Alembic is the only mechanism that changes the application schema. The manager
works with any configured absolute database path, which is what allows the
Phase 3 location wizard and the headless maintenance tool to reuse the same
code.

Startup policy is intentionally conservative:

* A database newer than the application's migration scripts is refused.
* A pending migration is reported but not applied automatically in Phase 2.
  Phase 4 adds the verified safety backup that must precede an upgrade
  (ARCHITECTURE.md ADR-007). Until then the maintenance tool performs the
  upgrade explicitly.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import DatabaseUnavailableError, MigrationError
from app.infrastructure.database.base import APPLICATION_ID
from app.infrastructure.database.engine import Database

logger = logging.getLogger(__name__)

_MIGRATIONS_ENV_VAR = "GOBINDAS_MIGRATIONS_DIR"


class MigrationState(StrEnum):
    """Relationship between the database revision and the application head."""

    UP_TO_DATE = "up_to_date"
    NOT_INITIALIZED = "not_initialized"
    UPGRADE_REQUIRED = "upgrade_required"
    NEWER_SCHEMA = "newer_schema"
    UNKNOWN_REVISION = "unknown_revision"


@dataclass(frozen=True, slots=True)
class MigrationStatus:
    current_revision: str | None
    head_revision: str | None
    state: MigrationState
    pending_revisions: tuple[str, ...] = ()

    @property
    def is_up_to_date(self) -> bool:
        return self.state is MigrationState.UP_TO_DATE

    @property
    def requires_upgrade(self) -> bool:
        return self.state is MigrationState.UPGRADE_REQUIRED

    @property
    def is_newer_than_application(self) -> bool:
        return self.state is MigrationState.NEWER_SCHEMA


@dataclass(frozen=True, slots=True)
class MigrationHistoryEntry:
    revision: str
    down_revision: str | None
    description: str


def default_migrations_dir() -> Path:
    """Resolve the migrations directory without relying on the CWD.

    A frozen build can override the location with ``GOBINDAS_MIGRATIONS_DIR``
    (the packaging phase will place the scripts next to the executable or in
    ``sys._MEIPASS``).
    """
    override = os.environ.get(_MIGRATIONS_ENV_VAR)
    if override:
        return Path(override)
    # app/infrastructure/database/migrations.py -> repository root
    return Path(__file__).resolve().parents[3] / "migrations"


def evaluate_migration_state(
    current_revision: str | None,
    head_revision: str | None,
    known_revisions: set[str],
) -> MigrationState:
    """Pure policy decision used by startup checks and tests."""
    if head_revision is None:
        raise MigrationError("the application has no migration scripts")
    if current_revision is None:
        return MigrationState.NOT_INITIALIZED
    if current_revision == head_revision:
        return MigrationState.UP_TO_DATE
    if current_revision not in known_revisions:
        return MigrationState.NEWER_SCHEMA
    return MigrationState.UPGRADE_REQUIRED


class MigrationManager:
    """Apply and inspect Alembic revisions for one :class:`Database`."""

    def __init__(self, database: Database, migrations_dir: Path | None = None) -> None:
        self._database = database
        self._migrations_dir = Path(migrations_dir or default_migrations_dir())
        self._config = Config()
        self._config.set_main_option("script_location", str(self._migrations_dir))
        # ConfigParser treats ``%`` as interpolation syntax. SQLAlchemy URL
        # strings percent-encode the Windows path, so escape the percent signs.
        self._config.set_main_option("sqlalchemy.url", str(database.config.url).replace("%", "%%"))

    @property
    def migrations_dir(self) -> Path:
        return self._migrations_dir

    @property
    def alembic_config(self) -> Config:
        return self._config

    def _script(self) -> ScriptDirectory:
        if not self._migrations_dir.is_dir():
            raise MigrationError(f"migrations directory not found: {self._migrations_dir}")
        return ScriptDirectory.from_config(self._config)

    def head_revision(self) -> str:
        head = self._script().get_current_head()
        if head is None:
            raise MigrationError("the application has no migration head")
        return head

    def known_revisions(self) -> set[str]:
        return {revision.revision for revision in self._script().walk_revisions()}

    def current_revision(self) -> str | None:
        """Read the database revision without creating the file."""
        if not self._database.config.path.exists():
            return None
        try:
            with self._database.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except (SQLAlchemyError, OSError) as exc:
            raise MigrationError(
                f"could not read the database schema revision: {exc}",
                user_message=(
                    "The database schema could not be read. The file may be damaged or "
                    "inaccessible. See the application log for details."
                ),
            ) from exc

    def status(self) -> MigrationStatus:
        head = self.head_revision()
        known = self.known_revisions()
        current = self.current_revision()
        state = evaluate_migration_state(current, head, known)
        pending: tuple[str, ...] = ()
        if state is MigrationState.UPGRADE_REQUIRED and current is not None:
            revisions = self._script().iterate_revisions(head, current)
            pending = tuple(revision.revision for revision in reversed(list(revisions)))
        return MigrationStatus(
            current_revision=current,
            head_revision=head,
            state=state,
            pending_revisions=pending,
        )

    def history(self) -> list[MigrationHistoryEntry]:
        entries: list[MigrationHistoryEntry] = []
        for revision in self._script().walk_revisions():
            down_revision = revision.down_revision
            entries.append(
                MigrationHistoryEntry(
                    revision=revision.revision,
                    down_revision=down_revision if isinstance(down_revision, str) else None,
                    description=revision.doc or "",
                )
            )
        return entries

    def create_database(self) -> MigrationStatus:
        """Create a new SQLite file and apply every migration.

        The parent directory must already exist. A database is created only by
        this explicit call, never by application startup.
        """
        self._database.config.require_absent_file()
        self._database.config.verify_writable_parent()
        logger.info("Creating database at %s", self._database.config.path)
        self._run_upgrade("head")
        status = self.status()
        if not status.is_up_to_date:
            raise MigrationError(
                f"database initialization ended in state {status.state}",
                user_message="The database could not be initialized completely.",
            )
        logger.info(
            "Database initialized at %s with schema revision %s",
            self._database.config.path,
            status.current_revision,
        )
        return status

    def upgrade(self, target: str = "head") -> MigrationStatus:
        """Upgrade an existing database. Missing files are never auto-created."""
        self._database.config.require_existing_file()
        self._run_upgrade(target)
        return self.status()

    def downgrade(self, target: str) -> MigrationStatus:
        """Downgrade an existing database to ``target`` (explicit request only)."""
        self._database.config.require_existing_file()
        try:
            with self._database.engine.begin() as connection:
                self._config.attributes["connection"] = connection
                command.downgrade(self._config, target)
        except Exception as exc:  # noqa: BLE001 - wrapped for the application boundary
            raise MigrationError(
                f"migration downgrade to {target} failed: {exc}",
                user_message=(
                    "The database schema could not be downgraded. The database was left "
                    "unchanged where SQLite supports transactional DDL."
                ),
            ) from exc
        finally:
            self._config.attributes.pop("connection", None)
        return self.status()

    def _run_upgrade(self, target: str) -> None:
        try:
            with self._database.engine.begin() as connection:
                self._config.attributes["connection"] = connection
                command.upgrade(self._config, target)
        except Exception as exc:  # noqa: BLE001 - wrapped for the application boundary
            raise MigrationError(
                f"migration upgrade to {target} failed: {exc}",
                user_message=(
                    "The database schema could not be updated. The application did not "
                    "continue with an incomplete schema. See the application log for details."
                ),
            ) from exc
        finally:
            self._config.attributes.pop("connection", None)


def read_application_id(database: Database) -> int | None:
    """Return the SQLite ``application_id`` header value, or None if unreadable."""
    with database.engine.connect() as connection:
        value = connection.exec_driver_sql("PRAGMA application_id").scalar()
    return int(value) if value is not None else None


def verify_database_for_startup(database: Database) -> MigrationStatus:
    """Validate an already-configured database before the UI is built.

    The check is deliberately light: it verifies the folder is writable, the
    file is accessible, the file identity, and the Alembic revision. It does not
    run a full integrity scan (that is an explicit maintenance action) and it
    never upgrades automatically.
    """
    database.config.verify_writable_parent()
    database.verify_accessible()
    try:
        application_id = read_application_id(database)
    except (SQLAlchemyError, OSError) as exc:
        raise DatabaseUnavailableError(
            f"database identity could not be read for {database.config.path}: {exc}",
            user_message=(
                "The database file could not be read. It may be damaged or inaccessible. "
                "The application will not change it."
            ),
        ) from exc

    if application_id not in (0, APPLICATION_ID):
        raise DatabaseUnavailableError(
            f"unexpected application_id {application_id} in {database.config.path}",
            user_message=(
                "The selected file is not a Gobindas Graphics database. Choose the correct "
                "database file; no changes were made."
            ),
        )

    manager = MigrationManager(database)
    status = manager.status()
    path = database.config.path

    if status.state is MigrationState.UP_TO_DATE:
        logger.info(
            "Database ready: %s | schema=%s | sqlite=%s",
            path,
            status.current_revision,
            database.sqlite_version(),
        )
        return status

    if status.state in (MigrationState.NOT_INITIALIZED, MigrationState.UPGRADE_REQUIRED):
        raise MigrationError(
            f"database schema revision {status.current_revision!r} requires migration to "
            f"{status.head_revision!r}",
            user_message=(
                "The database needs a schema update before this version can open it. "
                "No automatic upgrade was attempted. Run the migration tool or install the "
                "application version that matches this database."
            ),
        )

    raise MigrationError(
        f"database revision {status.current_revision!r} is not known to this application "
        f"(head {status.head_revision!r})",
        user_message=(
            "The database was created by a newer version of the application. Install the "
            "newer version; this version will not downgrade or modify the database."
        ),
    )


__all__ = [
    "MigrationHistoryEntry",
    "MigrationManager",
    "MigrationState",
    "MigrationStatus",
    "default_migrations_dir",
    "evaluate_migration_state",
    "read_application_id",
    "verify_database_for_startup",
]
