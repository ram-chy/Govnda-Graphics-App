"""Shared test fixtures.

Tests run with the offscreen Qt platform so they work on a headless runner and
do not open real windows.
"""

from __future__ import annotations

import logging
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig, ConfigService
from app.core.logging_config import HANDLER_MARKER


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication(["pytest"])
    return application


@pytest.fixture
def config_service(tmp_path) -> ConfigService:
    return ConfigService(tmp_path / "config" / "config.json")


@pytest.fixture
def default_config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def clean_logging_handlers():
    """Remove GGBMS handlers after a test so temporary log files can be deleted."""
    root = logging.getLogger()

    def remove_handlers() -> None:
        for handler in list(root.handlers):
            if getattr(handler, HANDLER_MARKER, False):
                root.removeHandler(handler)
                handler.close()

    remove_handlers()
    yield
    remove_handlers()
