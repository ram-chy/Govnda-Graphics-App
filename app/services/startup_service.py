"""Startup assessment: setup, recovery, or ready.

The service never creates or changes a database. It classifies the saved
configuration and, when a database is configured, runs the Phase 2 startup
verification before handing an open :class:`Database` to the composition root.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from app.core.config import AppConfig, ConfigLoadStatus, ConfigService
from app.core.exceptions import AppError
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import (
    DatabaseDiagnostics,
    DatabaseHealthReport,
    DatabaseHealthStatus,
)
from app.infrastructure.database.migrations import verify_database_for_startup
from app.infrastructure.filesystem.validation import DataLocationValidator

logger = logging.getLogger(__name__)


class StartupMode(StrEnum):
    """What the application shell must do before showing the business UI."""

    SETUP_REQUIRED = "setup_required"
    RECOVERY_REQUIRED = "recovery_required"
    READY = "ready"


class RecoveryReason(StrEnum):
    """Why normal startup cannot continue without the user's decision."""

    CORRUPT_CONFIGURATION = "corrupt_configuration"
    INCOMPLETE_CONFIGURATION = "incomplete_configuration"
    INVALID_LOCATION = "invalid_location"
    MISSING_DRIVE = "missing_drive"
    MISSING_FOLDER = "missing_folder"
    MISSING_DATABASE = "missing_database"
    PERMISSION_DENIED = "permission_denied"
    DATABASE_LOCKED = "database_locked"
    CORRUPT_DATABASE = "corrupt_database"
    WRONG_DATABASE = "wrong_database"
    INTEGRITY_ERROR = "integrity_error"
    MIGRATION_REQUIRED = "migration_required"
    MIGRATION_UNSUPPORTED = "migration_unsupported"
    DATABASE_UNAVAILABLE = "database_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class StartupAssessment:
    """The decision produced by :class:`StartupService`."""

    mode: StartupMode
    config: AppConfig
    config_status: ConfigLoadStatus
    quarantine_path: Path | None = None
    database: Database | None = None
    database_path: Path | None = None
    data_root: Path | None = None
    recovery_reason: RecoveryReason | None = None
    message: str = ""

    @property
    def is_ready(self) -> bool:
        return self.mode is StartupMode.READY


class StartupService:
    """Assess configuration and open the configured database safely."""

    def __init__(
        self,
        config_service: ConfigService,
        *,
        validator: DataLocationValidator | None = None,
    ) -> None:
        self._config_service = config_service
        self._validator = validator or DataLocationValidator()

    def assess(self) -> StartupAssessment:
        """Return the startup decision. Never creates a database or config file."""
        loaded = self._config_service.load_with_status()
        config = loaded.config

        if loaded.status is ConfigLoadStatus.RECOVERED:
            logger.warning(
                "Configuration recovery required; invalid file preserved at %s",
                loaded.quarantined_path,
            )
            return StartupAssessment(
                mode=StartupMode.RECOVERY_REQUIRED,
                config=config,
                config_status=loaded.status,
                quarantine_path=loaded.quarantined_path,
                recovery_reason=RecoveryReason.CORRUPT_CONFIGURATION,
                message=(
                    "The application settings file was invalid. The original file was "
                    "preserved for diagnosis and the default INR settings are in use. "
                    "Locate the existing business data or run setup again."
                ),
            )

        data_root = Path(config.data_root) if config.data_root else None
        if config.database_path is None:
            if data_root is None:
                logger.info("Setup required: no database location is configured")
                return StartupAssessment(
                    mode=StartupMode.SETUP_REQUIRED,
                    config=config,
                    config_status=loaded.status,
                    message="No business data location has been configured yet.",
                )
            return StartupAssessment(
                mode=StartupMode.RECOVERY_REQUIRED,
                config=config,
                config_status=loaded.status,
                data_root=data_root,
                recovery_reason=RecoveryReason.INCOMPLETE_CONFIGURATION,
                message=(
                    "A data folder is configured but no database file path is saved. "
                    "Locate the existing database or complete setup."
                ),
            )

        database_path = Path(config.database_path)
        if str(database_path).startswith("\\\\"):
            return self._recovery(
                config,
                loaded.status,
                reason=RecoveryReason.INVALID_LOCATION,
                message=(
                    "Network and UNC paths are not supported for the live database. "
                    "Choose a local fixed or removable drive."
                ),
                data_root=data_root,
                database_path=database_path,
            )
        if data_root is not None:
            validation = self._validator.validate(data_root)
            if not validation.is_valid:
                return self._recovery(
                    config,
                    loaded.status,
                    reason=self._reason_for_invalid_location(validation.errors[0].key),
                    message=validation.error_summary,
                    data_root=data_root,
                    database_path=database_path,
                )

        if not database_path.anchor or not Path(database_path.anchor).exists():
            return self._recovery(
                config,
                loaded.status,
                reason=RecoveryReason.MISSING_DRIVE,
                message=(
                    f"The drive for the configured database is not available "
                    f"({database_path.anchor}). Reconnect the drive, or locate the existing "
                    "business data on another drive. No replacement database was created."
                ),
                data_root=data_root,
                database_path=database_path,
            )

        if not database_path.parent.exists():
            return self._recovery(
                config,
                loaded.status,
                reason=RecoveryReason.MISSING_FOLDER,
                message=(
                    f"The configured database folder does not exist ({database_path.parent}). "
                    "Reconnect the drive or locate the existing business data. No replacement "
                    "database was created."
                ),
                data_root=data_root,
                database_path=database_path,
            )

        if not database_path.exists():
            return self._recovery(
                config,
                loaded.status,
                reason=RecoveryReason.MISSING_DATABASE,
                message=(
                    f"The configured database file does not exist ({database_path}). "
                    "Locate the existing business data or confirm a new setup explicitly. "
                    "No replacement database was created."
                ),
                data_root=data_root,
                database_path=database_path,
            )

        if not database_path.is_file():
            return self._recovery(
                config,
                loaded.status,
                reason=RecoveryReason.INVALID_LOCATION,
                message=(
                    f"The configured database path is not a file ({database_path}). "
                    "Choose the correct data location."
                ),
                data_root=data_root,
                database_path=database_path,
            )

        database = Database(DatabaseConfig(path=database_path))
        try:
            report = DatabaseDiagnostics(database).check(full=False)
            if not report.healthy:
                database.shutdown()
                return self._recovery_from_health(
                    config,
                    loaded.status,
                    report,
                    data_root=data_root,
                    database_path=database_path,
                )
            verify_database_for_startup(database)
        except AppError as exc:
            database.shutdown()
            return self._recovery(
                config,
                loaded.status,
                reason=RecoveryReason.DATABASE_UNAVAILABLE,
                message=exc.user_message,
                data_root=data_root,
                database_path=database_path,
            )
        except BaseException:
            database.shutdown()
            raise

        logger.info(
            "Startup ready: database=%s | data_root=%s",
            database_path,
            data_root or "(legacy configuration)",
        )
        return StartupAssessment(
            mode=StartupMode.READY,
            config=config,
            config_status=loaded.status,
            database=database,
            database_path=database_path,
            data_root=data_root,
            message="The configured database is ready.",
        )

    def _recovery(
        self,
        config: AppConfig,
        status: ConfigLoadStatus,
        *,
        reason: RecoveryReason,
        message: str,
        data_root: Path | None = None,
        database_path: Path | None = None,
    ) -> StartupAssessment:
        logger.warning("Startup recovery required (%s): %s", reason.value, message)
        return StartupAssessment(
            mode=StartupMode.RECOVERY_REQUIRED,
            config=config,
            config_status=status,
            data_root=data_root,
            database_path=database_path,
            recovery_reason=reason,
            message=message,
        )

    def _recovery_from_health(
        self,
        config: AppConfig,
        status: ConfigLoadStatus,
        report: DatabaseHealthReport,
        *,
        data_root: Path | None,
        database_path: Path,
    ) -> StartupAssessment:
        reason = _reason_for_health(report.status)
        if report.status is DatabaseHealthStatus.UNAVAILABLE_PATH and not Path(
            database_path.anchor
        ).exists():
            reason = RecoveryReason.MISSING_DRIVE
        return self._recovery(
            config,
            status,
            reason=reason,
            message=report.message,
            data_root=data_root,
            database_path=database_path,
        )

    @staticmethod
    def _reason_for_invalid_location(check_key: str) -> RecoveryReason:
        if check_key == "drive_available":
            return RecoveryReason.MISSING_DRIVE
        if check_key in {"directory", "parent"}:
            return RecoveryReason.MISSING_FOLDER
        if check_key in {"read", "write", "protected"}:
            return RecoveryReason.PERMISSION_DENIED
        return RecoveryReason.INVALID_LOCATION


def _reason_for_health(status: DatabaseHealthStatus) -> RecoveryReason:
    return {
        DatabaseHealthStatus.MISSING_DATABASE: RecoveryReason.MISSING_DATABASE,
        DatabaseHealthStatus.UNAVAILABLE_PATH: RecoveryReason.MISSING_FOLDER,
        DatabaseHealthStatus.PERMISSION_DENIED: RecoveryReason.PERMISSION_DENIED,
        DatabaseHealthStatus.LOCKED: RecoveryReason.DATABASE_LOCKED,
        DatabaseHealthStatus.CORRUPT: RecoveryReason.CORRUPT_DATABASE,
        DatabaseHealthStatus.WRONG_DATABASE: RecoveryReason.WRONG_DATABASE,
        DatabaseHealthStatus.FOREIGN_KEYS_DISABLED: RecoveryReason.DATABASE_UNAVAILABLE,
        DatabaseHealthStatus.INTEGRITY_ERROR: RecoveryReason.INTEGRITY_ERROR,
        DatabaseHealthStatus.MIGRATION_REQUIRED: RecoveryReason.MIGRATION_REQUIRED,
        DatabaseHealthStatus.MIGRATION_FAILED: RecoveryReason.MIGRATION_UNSUPPORTED,
        DatabaseHealthStatus.UNKNOWN_ERROR: RecoveryReason.UNKNOWN,
    }.get(status, RecoveryReason.UNKNOWN)


__all__ = ["RecoveryReason", "StartupAssessment", "StartupMode", "StartupService"]
