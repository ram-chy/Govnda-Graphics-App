"""Headless backup runner used by Windows Task Scheduler.

The runner is a thin, Qt-free entry point around the same services the GUI uses.
It never creates a database, never invents a data root, never touches another
location when the configured drive is missing, and never publishes a backup that
failed verification.

Exit codes are stable so Task Scheduler and the manual Windows test procedure can
assert the outcome:

* ``0`` - a verified backup was published (retention ran afterwards)
* ``1`` - the backup failed; no incomplete file was published
* ``2`` - configuration is missing, unreadable, or has no usable data root
* ``3`` - another backup, restore, relocation, or upgrade holds the operation lock

Examples::

    python -m app.tools.backup
    python -m app.tools.backup --scheduled --config "%APPDATA%\\GobindasBMS\\config.json"
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core import constants
from app.core.config import AppConfig, ConfigLoadStatus, ConfigService
from app.core.exceptions import AppError, BackupError, ConfigurationError, OperationLockedError
from app.core.logging_config import configure_logging
from app.core.paths import default_paths
from app.domain.backup import BackupType
from app.services.backup_service import BackupResult
from app.services.backup_workspace import BackupWorkspace, BackupWorkspaceFactory
from app.services.database_runtime import DatabaseRuntime

logger = logging.getLogger("app.tools.backup")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.tools.backup",
        description=(
            "Create one verified backup of the configured business database. The command "
            "refuses to run without a saved data location."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Absolute path to config.json (default: the per-user application configuration).",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Mark the run as the scheduled automatic backup.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Log verbosity for the runner process.",
    )
    return parser


def _resolve_config_path(raw: Path | None) -> Path:
    path = raw if raw is not None else default_paths().config_file
    if not path.is_absolute():
        path = path.resolve()
    return path


def _load_config(config_service: ConfigService) -> AppConfig:
    loaded = config_service.load_with_status(quarantine_invalid=False)
    if loaded.status is not ConfigLoadStatus.LOADED:
        raise ConfigurationError(
            f"no usable configuration at {config_service.config_path}",
            user_message=(
                "The backup runner could not read the application settings. Run the "
                "application once and complete setup before enabling automatic backups."
            ),
        )
    if loaded.config.data_root is None or loaded.config.database_path is None:
        raise ConfigurationError(
            "the configuration does not record a data root and database path",
            user_message=(
                "The backup runner has no business data location to back up. Complete "
                "setup in the application first."
            ),
        )
    return loaded.config


def run_backup(
    *,
    config_path: Path,
    scheduled: bool,
    factory: BackupWorkspaceFactory | None = None,
) -> int:
    """Run one backup and return a stable exit code."""
    config_service = ConfigService(config_path)
    try:
        config = _load_config(config_service)
        runtime = DatabaseRuntime()
        workspace_factory = factory or BackupWorkspaceFactory(config_service, runtime)
        workspace = workspace_factory.build(config)
    except ConfigurationError as exc:
        logger.error("Backup runner configuration error: %s", exc)
        _print_error(exc.user_message)
        return constants.BACKUP_EXIT_CONFIGURATION
    except AppError as exc:
        logger.error("Backup runner could not start: %s", exc)
        _print_error(exc.user_message)
        return constants.BACKUP_EXIT_CONFIGURATION

    backup_type = BackupType.AUTOMATIC if scheduled else BackupType.MANUAL
    trigger = "scheduled" if scheduled else "runner"

    try:
        result = workspace.backup_service.create_backup(backup_type, trigger=trigger)
    except OperationLockedError as exc:
        logger.warning("Backup runner skipped: another operation holds the lock (%s)", exc)
        _print_error(exc.user_message)
        return constants.BACKUP_EXIT_LOCKED
    except BackupError as exc:
        logger.error("Backup runner failed: %s", exc)
        _print_error(exc.user_message)
        return constants.BACKUP_EXIT_FAILURE
    except Exception:  # noqa: BLE001 - process boundary must map to an exit code
        logger.exception("Backup runner failed unexpectedly")
        _print_error(
            "The backup could not be created. See the application log for details."
        )
        return constants.BACKUP_EXIT_FAILURE

    _report_success(result)
    _apply_retention(workspace)
    return constants.BACKUP_EXIT_SUCCESS


def _apply_retention(workspace: BackupWorkspace) -> None:
    """Apply retention after a successful backup; never fail the backup for it."""
    config = workspace.config
    try:
        result = workspace.retention_service.apply(
            retention_days=config.backup_retention_days,
            keep_minimum=config.backup_keep_minimum,
        )
    except OperationLockedError:
        logger.info("Retention skipped because another operation holds the lock")
        return
    except AppError as exc:
        logger.warning("Retention could not be applied: %s", exc)
        return
    except Exception:  # noqa: BLE001 - retention must not invalidate a good backup
        logger.exception("Retention failed unexpectedly")
        return
    if result.errors:
        logger.warning(
            "Retention completed with %d error(s): %s",
            len(result.errors),
            "; ".join(result.errors),
        )


def _report_success(result: BackupResult) -> None:
    message = (
        f"backup verified: {result.record.file_name} "
        f"({result.metadata.backup_bytes} bytes, sha256 {result.metadata.sha256[:12]}...)"
    )
    logger.info(message)
    print(message)


def _print_error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    paths = default_paths()
    try:
        paths.ensure_directories()
    except OSError:
        print("error: the application directories could not be created", file=sys.stderr)
        return constants.BACKUP_EXIT_CONFIGURATION

    configure_logging(
        paths.log_file(),
        level=args.log_level,
        console=bool(sys.stderr is not None and sys.stderr.isatty()),
    )

    config_path = _resolve_config_path(args.config)
    logger.info(
        "Backup runner starting (scheduled=%s, config=%s, app=%s)",
        args.scheduled,
        config_path,
        constants.APP_VERSION,
    )
    return run_backup(config_path=config_path, scheduled=args.scheduled)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "run_backup"]
