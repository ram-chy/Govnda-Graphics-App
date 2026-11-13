"""Application entry point (composition root).

Startup order: logging, configuration, Qt application, single-instance guard,
theme, main window, event loop. Business logic must not live here.
"""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from app.app_context import AppContext
from app.core import constants
from app.core.error_handling import install_excepthook
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging, new_correlation_id
from app.core.paths import default_paths
from app.core.single_instance import SingleInstanceGuard
from app.ui.dialogs.error_dialog import show_fatal_error
from app.ui.main_window import MainWindow
from app.ui.themes.manager import ThemeManager
from app.ui.viewmodels.shell_viewmodel import ShellViewModel

logger = logging.getLogger("app.main")

SMOKE_TEST_FLAG = "--smoke-test"
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


def run(argv: list[str] | None = None) -> int:
    """Run the desktop application and return a process exit code."""
    arguments = list(sys.argv if argv is None else argv)
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
        None if smoke_test else lambda correlation_id, _exc: show_fatal_error(
            None, correlation_id, log_file
        )
    )

    guard = SingleInstanceGuard(
        os.environ.get("GOBINDAS_MUTEX_NAME", constants.MUTEX_NAME)
    )
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

    try:
        context = AppContext.create(paths)

        # Apply the configured level now that the configuration is trusted.
        log_file = configure_logging(
            paths.log_file(),
            level=context.config.log_level,
            console=_console_logging_enabled(),
        )
        _log_startup_context(context)

        theme_manager = ThemeManager(application)
        viewmodel = ShellViewModel(context.config_service, context.config)
        window = MainWindow(viewmodel, theme_manager)
        window.show()

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
        guard.release()
        logger.info("Application exiting")
        logging.shutdown()


__all__ = ["create_application", "main", "run"]


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
