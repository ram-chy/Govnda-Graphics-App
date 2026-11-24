"""Application entry point (composition root).

Startup order: logging, Qt application, single-instance guard, startup
assessment (setup / recovery / ready), theme, window, event loop. Business logic
must not live here.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from app.app_context import AppContext
from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.core.error_handling import install_excepthook
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging, new_correlation_id
from app.core.paths import AppPaths, default_paths
from app.core.single_instance import SingleInstanceGuard
from app.services.setup_service import SetupResult, SetupService
from app.services.startup_service import (
    RecoveryReason,
    StartupAssessment,
    StartupMode,
    StartupService,
)
from app.ui.dialogs.auth_dialogs import FirstRunDialog, LoginDialog
from app.ui.dialogs.error_dialog import show_fatal_error
from app.ui.dialogs.recovery_dialog import RecoveryAction, RecoveryDialog
from app.ui.dialogs.setup_wizard import SetupWizard
from app.ui.main_window import MainWindow
from app.ui.themes.manager import ThemeManager
from app.ui.viewmodels.shell_viewmodel import ShellViewModel

logger = logging.getLogger("app.main")

SMOKE_TEST_FLAG = "--smoke-test"
RUN_BACKUP_FLAG = "--run-backup"
SMOKE_TEST_DURATION_MS = 1200


def create_application(argv: list[str]) -> QApplication:
    """Create and configure the QApplication instance."""
    application = QApplication(argv)
    application.setApplicationName(constants.APP_NAME)
    application.setApplicationDisplayName(constants.APP_SHORT_NAME)
    application.setApplicationVersion(constants.APP_VERSION)
    application.setOrganizationName(constants.ORGANIZATION_NAME)
    return application


def _console_logging_enabled() -> bool:
    return bool(sys.stderr is not None and sys.stderr.isatty())


def _set_high_dpi_policy() -> None:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def _log_startup_context(context: AppContext) -> None:
    logger.info(
        "Starting %s %s on Python %s",
        constants.APP_NAME,
        constants.APP_VERSION,
        sys.version.split()[0],
    )
    logger.info(
        "Configuration: %s | theme=%s | currency=%s | log level=%s",
        context.paths.config_file,
        context.config.theme,
        context.config.currency_code,
        context.config.log_level,
    )
    if context.database is None:
        logger.info("Database: not configured")
    else:
        logger.info(
            "Database: %s | data root=%s | busy_timeout=%d ms",
            context.database.config.path,
            context.config.data_root or "(legacy configuration)",
            context.database.config.busy_timeout_ms,
        )


def _run_setup_wizard(
    service: SetupService,
    base_config: AppConfig,
    *,
    initial_path: str | None = None,
) -> SetupResult | None:
    wizard = SetupWizard(service, base_config, initial_path=initial_path)
    if wizard.exec() == QDialog.DialogCode.Accepted:
        return wizard.take_result()
    return None


def _recovery_start_directory(assessment: StartupAssessment) -> str:
    candidates = (assessment.data_root, assessment.database_path)
    for candidate in candidates:
        if candidate is None:
            continue
        if candidate.is_dir():
            return str(candidate)
        if candidate.parent.is_dir():
            return str(candidate.parent)
    return str(Path.home())


def _run_recovery(
    startup: StartupService,
    config_service: ConfigService,
    paths: AppPaths,
    assessment: StartupAssessment,
) -> AppContext | None:
    """Loop the blocking recovery workflow until a database is ready or the user exits."""
    service = SetupService(config_service)
    current = assessment
    while current.mode is StartupMode.RECOVERY_REQUIRED:
        dialog = RecoveryDialog(
            current.message,
            database_path=current.database_path,
            data_root=current.data_root,
            quarantine_path=current.quarantine_path,
        )
        dialog.exec()
        action = dialog.action

        if action is RecoveryAction.EXIT:
            logger.info("Recovery: user chose to exit")
            return None
        if action is RecoveryAction.RETRY:
            current = startup.assess()
            continue
        if action is RecoveryAction.LOCATE:
            chosen = QFileDialog.getExistingDirectory(
                None,
                "Locate the existing business data folder",
                _recovery_start_directory(current),
            )
            if not chosen:
                continue
            try:
                result = service.attach_existing(Path(chosen), base_config=current.config)
            except AppError as exc:
                QMessageBox.critical(
                    None,
                    "Existing business data could not be opened",
                    exc.user_message,
                )
                continue
            return AppContext.from_parts(
                paths,
                config=result.config,
                config_service=config_service,
                database=result.database,
            )
        if action is RecoveryAction.NEW_SETUP:
            result = _run_setup_wizard(
                service,
                current.config,
                initial_path=_recovery_start_directory(current),
            )
            if result is not None:
                return AppContext.from_parts(
                    paths,
                    config=result.config,
                    config_service=config_service,
                    database=result.database,
                )
            current = startup.assess()
            continue
    return None


def _schedule_startup_catch_up(window: MainWindow, context: AppContext) -> None:
    """Ask the window to run a missed backup in the background after startup.

    The delay keeps first paint responsive. The window owns the worker so a
    closing application can cancel it cleanly.
    """
    if not context.config.backup_enabled:
        logger.info("Startup catch-up skipped: automatic backups are disabled")
        return
    QTimer.singleShot(
        constants.CATCH_UP_DELAY_MS,
        window,
        window.run_startup_catch_up,
    )


def run(argv: list[str] | None = None) -> int:
    """Run the desktop application and return a process exit code."""
    arguments = list(sys.argv if argv is None else argv)

    # A packaged build is started with ``--run-backup`` by Task Scheduler. The
    # backup must be possible while the GUI is closed, so this dispatch happens
    # before Qt, logging, and the single-instance mutex. The runner has its own
    # cross-process operation lock.
    if RUN_BACKUP_FLAG in arguments:
        arguments.remove(RUN_BACKUP_FLAG)
        from app.tools.backup import main as run_backup_tool

        return run_backup_tool(arguments)

    smoke_test = SMOKE_TEST_FLAG in arguments
    if smoke_test:
        arguments.remove(SMOKE_TEST_FLAG)

    paths = default_paths()
    try:
        paths.ensure_directories()
    except OSError:
        logging.basicConfig(level=logging.INFO)
        logger.exception("Application directories could not be created")
        return 1

    log_file = configure_logging(
        paths.log_file(),
        level=constants.DEFAULT_LOG_LEVEL,
        console=_console_logging_enabled(),
    )

    _set_high_dpi_policy()
    application = create_application(arguments)

    install_excepthook(
        None
        if smoke_test
        else lambda correlation_id, _exc: show_fatal_error(None, correlation_id, log_file)
    )

    guard = SingleInstanceGuard(os.environ.get("GOBINDAS_MUTEX_NAME", constants.MUTEX_NAME))
    try:
        acquired = guard.acquire()
    except OSError:
        correlation_id = new_correlation_id()
        logger.critical(
            "Single-instance guard failed [%s]",
            correlation_id,
            exc_info=True,
            extra={"correlation_id": correlation_id},
        )
        if not smoke_test:
            show_fatal_error(None, correlation_id, log_file)
        return 1

    if not acquired:
        logger.info("Another application instance is already running; exiting")
        if not smoke_test:
            QMessageBox.information(
                None,
                constants.APP_SHORT_NAME,
                "Gobindas Graphics Business Management System is already running.",
            )
        logging.shutdown()
        return 0

    context: AppContext | None = None
    try:
        config_service = ConfigService(paths.config_file)
        startup = StartupService(config_service)
        assessment = startup.assess()

        log_file = configure_logging(
            paths.log_file(),
            level=assessment.config.log_level,
            console=_console_logging_enabled(),
        )

        theme_manager = ThemeManager(application)
        theme_manager.apply(assessment.config.theme)

        if assessment.mode is StartupMode.SETUP_REQUIRED:
            if smoke_test:
                logger.info(
                    "Setup required: no database location is configured. "
                    "Smoke test exiting without opening a window."
                )
                return 0
            logger.info("First-launch setup required")
            result = _run_setup_wizard(SetupService(config_service), assessment.config)
            if result is None:
                logger.info("First-launch setup cancelled; no database was created")
                return 0
            context = AppContext.from_parts(
                paths,
                config=result.config,
                config_service=config_service,
                database=result.database,
            )
        elif assessment.mode is StartupMode.RECOVERY_REQUIRED:
            if smoke_test:
                correlation_id = new_correlation_id()
                logger.error(
                    "Startup recovery required [%s] (%s): %s",
                    correlation_id,
                    assessment.recovery_reason.value
                    if assessment.recovery_reason is not None
                    else RecoveryReason.UNKNOWN.value,
                    assessment.message,
                    extra={"correlation_id": correlation_id},
                )
                return 1
            logger.info(
                "Startup recovery required (%s)",
                assessment.recovery_reason.value
                if assessment.recovery_reason is not None
                else RecoveryReason.UNKNOWN.value,
            )
            context = _run_recovery(startup, config_service, paths, assessment)
            if context is None:
                logger.info("Recovery exited without opening the application")
                return 0
        else:
            if assessment.database is None:  # pragma: no cover - defensive
                raise RuntimeError("startup assessment reported ready without a database")
            context = AppContext.from_parts(
                paths,
                config=assessment.config,
                config_service=config_service,
                database=assessment.database,
            )

        if context.auth_services is None:
            raise RuntimeError("Authentication services are unavailable")

        auth = context.auth_services
        if smoke_test:
            # Smoke tests exercise the shell only. Bypassing the interactive gate
            # avoids writing a known-credential account into the configured DB.
            logger.info("Smoke test: skipping interactive authentication gate")
        else:
            if not auth.authentication.has_accounts():
                first_run = FirstRunDialog(auth.authentication)
                if first_run.exec() != QDialog.DialogCode.Accepted:
                    logger.info("First-run owner setup cancelled")
                    return 0

            login = LoginDialog(auth.authentication)
            if login.exec() != QDialog.DialogCode.Accepted:
                logger.info("Login cancelled; exiting")
                return 0

        _log_startup_context(context)

        viewmodel = ShellViewModel(context.config_service, context.config)
        window = MainWindow(
            viewmodel,
            theme_manager,
            database_path=context.database_path,
            data_root=Path(context.config.data_root) if context.config.data_root else None,
            config_service=context.config_service,
            database_runtime=context.runtime,
            workspace_factory=context.workspace_factory,
            business_profile_factory=context.business_profile_factory,
            party_factory=context.party_factory,
            catalogue_factory=context.catalogue_factory,
            auth_services=auth,
        )
        window.show()

        _schedule_startup_catch_up(window, context)

        application.aboutToQuit.connect(lambda: logger.info("Application shutdown requested"))
        logger.info("Main window shown")

        if smoke_test:
            logger.info("Smoke test mode: quitting automatically")
            QTimer.singleShot(SMOKE_TEST_DURATION_MS, application.quit)

        return application.exec()
    except AppError as exc:
        correlation_id = new_correlation_id()
        logger.error(
            "Startup failed [%s]: %s",
            correlation_id,
            exc,
            exc_info=True,
            extra={"correlation_id": correlation_id},
        )
        if not smoke_test:
            show_fatal_error(
                None,
                correlation_id,
                log_file,
                message=exc.user_message,
            )
        return 1
    except Exception as exc:  # noqa: BLE001 - last-resort startup guard
        correlation_id = new_correlation_id()
        logger.critical(
            "Unexpected startup failure [%s]: %s",
            correlation_id,
            exc,
            exc_info=True,
            extra={"correlation_id": correlation_id},
        )
        if not smoke_test:
            show_fatal_error(None, correlation_id, log_file)
        return 1
    finally:
        if context is not None:
            context.close()
        guard.release()
        logger.info("Application exiting")
        logging.shutdown()


__all__ = ["create_application", "main", "run"]


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
