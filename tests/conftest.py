"""Shared test fixtures.

Tests run with the offscreen Qt platform so they work on a headless runner and
do not open real windows.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig, ConfigService
from app.core.logging_config import HANDLER_MARKER
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication(["pytest"])
    return application


@pytest.fixture
def db_dir(tmp_path) -> Path:
    """An existing folder for a temporary database (never the real data folder)."""
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


@pytest.fixture
def database_config(db_dir: Path) -> DatabaseConfig:
    return DatabaseConfig(path=db_dir / "test.db")


@pytest.fixture
def initialized_database(database_config: DatabaseConfig) -> Database:
    """A temporary database at the baseline schema, disposed after the test."""
    database = Database(database_config)
    MigrationManager(database).create_database()
    try:
        yield database
    finally:
        database.shutdown()


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
