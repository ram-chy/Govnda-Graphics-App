"""First-launch setup orchestration.

The service validates a user-selected data root, creates the approved folder
layout, initializes or adopts a SQLite database through the Phase 2 migration
manager, verifies it, and only then persists the location atomically in the
application configuration.

Safety rules enforced here:

* No path is ever derived from the working directory or the installation folder.
* An existing database file is never overwritten, truncated, or migrated.
* Configuration is written only after the database is initialized and verified.
* If configuration persistence fails, the verified database is retained so the
  user can retry the save without repeating the data work.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from app.core.config import AppConfig, ConfigService
from app.core.exceptions import AppError, ConfigurationError, SetupError
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import (
    DatabaseDiagnostics,
    DatabaseHealthReport,
)
from app.infrastructure.database.migrations import (
    MigrationManager,
    MigrationStatus,
    verify_database_for_startup,
)
from app.infrastructure.filesystem.layout import DataRootLayout
from app.infrastructure.filesystem.scaffold import DataRootScaffolder, ScaffoldResult
from app.infrastructure.filesystem.validation import (
    DataLocationValidator,
    LocationValidationResult,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]

_PRESERVED_FIELDS = (
    "schema_version",
    "currency_code",
    "currency_symbol",
    "currency_decimal_places",
    "currency_grouping",
    "theme",
    "log_level",
)


@dataclass(frozen=True, slots=True)
class SetupResult:
    """A verified database and the configuration that describes it."""

    layout: DataRootLayout
    database: Database
    base_config: AppConfig
    config: AppConfig
    migration: MigrationStatus
    health: DatabaseHealthReport
    scaffold: ScaffoldResult
    adopted_existing_database: bool

    @property
    def data_root(self) -> Path:
        return self.layout.root

    @property
    def database_path(self) -> Path:
        return self.layout.database_path


class SetupPersistenceError(SetupError):
    """The database is ready but its location could not be saved.

    ``result`` owns an open, verified database. The caller may call
    :meth:`SetupService.persist` again after fixing the configuration problem.
    """

    def __init__(
        self,
        message: str,
        *,
        result: SetupResult,
        user_message: str | None = None,
    ) -> None:
        super().__init__(message, user_message=user_message)
        self.result = result


class SetupService:
    """Validate, scaffold, initialize, verify, and persist one data location."""

    def __init__(
        self,
        config_service: ConfigService,
        *,
        validator: DataLocationValidator | None = None,
        scaffolder: DataRootScaffolder | None = None,
        migrations_dir: Path | None = None,
    ) -> None:
        self._config_service = config_service
        self._validator = validator or DataLocationValidator()
        self._scaffolder = scaffolder or DataRootScaffolder()
        self._migrations_dir = migrations_dir

    def validate(self, raw_path: str | Path | None) -> LocationValidationResult:
        """Validate a candidate data root. This never creates anything."""
        return self._validator.validate(raw_path)

    def initialize(
        self,
        data_root: str | Path,
        *,
        base_config: AppConfig | None = None,
        progress: ProgressCallback | None = None,
    ) -> SetupResult:
        """Create or safely adopt a database under ``data_root``.

        An existing database is adopted only when it passes identity, migration,
        and full health checks. It is never overwritten or upgraded here.
        """
        layout = self._validated_layout(data_root)
        return self._run(
            layout,
            require_existing_database=False,
            base_config=base_config,
            progress=progress,
        )

    def attach_existing(
        self,
        data_root: str | Path,
        *,
        base_config: AppConfig | None = None,
        progress: ProgressCallback | None = None,
    ) -> SetupResult:
        """Connect to an existing database without ever creating one."""
        layout = self._validated_layout(data_root)
        return self._run(
            layout,
            require_existing_database=True,
            base_config=base_config,
            progress=progress,
        )

    def persist(self, result: SetupResult) -> AppConfig:
        """Retry saving a verified setup result and return the reloaded config."""
        try:
            return self._persist(result)
        except ConfigurationError as exc:
            raise SetupPersistenceError(
                str(exc),
                result=result,
                user_message=(
                    "The database was created and verified, but its location could not be "
                    "saved in the application settings. The database was not deleted. "
                    "Check that the settings folder is writable and retry."
                ),
            ) from exc

    def _validated_layout(self, data_root: str | Path) -> DataRootLayout:
        validation = self._validator.validate(data_root)
        if not validation.is_valid or validation.layout is None:
            raise SetupError(
                "selected data location is not valid",
                user_message=validation.error_summary,
            )
        return validation.layout

    def _run(
        self,
        layout: DataRootLayout,
        *,
        require_existing_database: bool,
        base_config: AppConfig | None,
        progress: ProgressCallback | None,
    ) -> SetupResult:
        database: Database | None = None
        scaffold: ScaffoldResult | None = None
        try:
            if require_existing_database and not layout.database_path.exists():
                raise SetupError(
                    f"no existing database at {layout.database_path}",
                    user_message=(
                        f"No database file was found at {layout.database_path}. "
                        "Choose the folder that contains the existing business data. "
                        "No new database was created."
                    ),
                )

            self._report(progress, "Checking the selected folder")
            scaffold = self._scaffolder.create(layout)

            self._report(progress, "Preparing the database")
            if layout.database_path.exists():
                database, migration, adopted = self._adopt_existing(layout)
            else:
                database, migration, adopted = self._create_database(layout)

            self._report(progress, "Verifying database integrity")
            health = self._verify_health(database)

            self._report(progress, "Saving the data location")
            base = base_config if base_config is not None else self._config_service.load()
            result = SetupResult(
                layout=layout,
                database=database,
                base_config=base,
                config=base,
                migration=migration,
                health=health,
                scaffold=scaffold,
                adopted_existing_database=adopted,
            )
            saved = self.persist(result)
            return replace(result, config=saved)
        except SetupPersistenceError:
            # The verified database must stay open so the user can retry the save.
            raise
        except BaseException:
            if database is not None:
                database.shutdown()
            if scaffold is not None:
                self._scaffolder.cleanup(scaffold)
            raise

    def _create_database(
        self, layout: DataRootLayout
    ) -> tuple[Database, MigrationStatus, bool]:
        database = Database(DatabaseConfig(path=layout.database_path))
        try:
            manager = MigrationManager(database, self._migrations_dir)
            status = manager.create_database()
        except BaseException:
            database.shutdown()
            raise

        logger.info(
            "Setup created database %s at schema revision %s",
            layout.database_path,
            status.current_revision,
        )
        return database, status, False

    def _adopt_existing(
        self, layout: DataRootLayout
    ) -> tuple[Database, MigrationStatus, bool]:
        logger.info("Setup is checking the existing database at %s", layout.database_path)
        database = Database(DatabaseConfig(path=layout.database_path))
        try:
            status = verify_database_for_startup(database)
        except AppError as exc:
            database.shutdown()
            raise SetupError(str(exc), user_message=exc.user_message) from exc
        except BaseException:
            database.shutdown()
            raise
        return database, status, True

    def _verify_health(self, database: Database) -> DatabaseHealthReport:
        report = DatabaseDiagnostics(database).check(full=True)
        if report.healthy:
            return report
        database.shutdown()
        raise SetupError(
            f"database health check failed with {report.status.value}: {report.message}",
            user_message=(
                f"The database did not pass verification: {report.message} "
                "No file was deleted or overwritten. Choose another location or try again."
            ),
        )

    def _persist(self, result: SetupResult) -> AppConfig:
        updated = result.base_config.with_database_location(
            data_root=result.layout.root,
            database_path=result.layout.database_path,
        )
        self._config_service.save(updated)
        reloaded = self._config_service.load()
        self._verify_persisted(reloaded, result)
        logger.info(
            "Configuration saved: data_root=%s | database=%s",
            reloaded.data_root,
            reloaded.database_path,
        )
        return reloaded

    @staticmethod
    def _verify_persisted(reloaded: AppConfig, result: SetupResult) -> None:
        if reloaded.data_root is None or Path(reloaded.data_root) != result.layout.root:
            raise ConfigurationError(
                "saved data_root does not match the selected data root",
                user_message=(
                    "The settings file did not read back the selected data folder. "
                    "The database is intact; retry saving the location."
                ),
            )
        if (
            reloaded.database_path is None
            or Path(reloaded.database_path) != result.layout.database_path
        ):
            raise ConfigurationError(
                "saved database_path does not match the selected database file",
                user_message=(
                    "The settings file did not read back the selected database path. "
                    "The database is intact; retry saving the location."
                ),
            )
        for field in _PRESERVED_FIELDS:
            if getattr(reloaded, field) != getattr(result.base_config, field):
                raise ConfigurationError(
                    f"saved configuration changed preserved field {field}",
                    user_message=(
                        "Existing application settings could not be preserved while saving "
                        "the data location. The database is intact; review the settings "
                        "and retry."
                    ),
                )

    @staticmethod
    def _report(progress: ProgressCallback | None, message: str) -> None:
        logger.info("Setup: %s", message)
        if progress is not None:
            progress(message)


__all__ = ["SetupPersistenceError", "SetupResult", "SetupService"]
