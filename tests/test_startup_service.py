"""Startup assessment and recovery classification."""

from __future__ import annotations

import json
import sqlite3
import string
from pathlib import Path

from app.core.config import AppConfig, ConfigLoadStatus, ConfigService
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager
from app.services.startup_service import (
    RecoveryReason,
    StartupMode,
    StartupService,
)


def _create_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(DatabaseConfig(path=database_path))
    try:
        MigrationManager(database).create_database()
    finally:
        database.shutdown()


def _config_service(tmp_path: Path) -> ConfigService:
    return ConfigService(tmp_path / "config" / "config.json")


def _configure(
    config_service: ConfigService, data_root: Path | None, database_path: Path
) -> None:
    config = AppConfig(
        data_root=str(data_root) if data_root is not None else None,
        database_path=str(database_path),
    )
    config_service.save(config)


def _missing_drive() -> str:
    for letter in reversed(string.ascii_uppercase):
        candidate = f"{letter}:\\"
        if not Path(candidate).exists():
            return candidate
    raise AssertionError("every drive letter is in use on this machine")


def test_no_configuration_requires_first_launch_setup(tmp_path: Path) -> None:
    assessment = StartupService(_config_service(tmp_path)).assess()

    assert assessment.mode is StartupMode.SETUP_REQUIRED
    assert assessment.config_status is ConfigLoadStatus.MISSING
    assert assessment.database is None
    assert assessment.database_path is None
    assert assessment.data_root is None
    assert not _config_service(tmp_path).config_path.exists()


def test_corrupt_configuration_requires_recovery_and_is_preserved(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text("{ not json", encoding="utf-8")

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.config_status is ConfigLoadStatus.RECOVERED
    assert assessment.recovery_reason is RecoveryReason.CORRUPT_CONFIGURATION
    assert assessment.quarantine_path is not None
    assert assessment.quarantine_path.is_file()
    assert assessment.quarantine_path.read_text(encoding="utf-8") == "{ not json"
    assert assessment.config == AppConfig()
    assert not config_service.config_path.exists()


def test_data_root_without_database_path_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    config_service.save(AppConfig(data_root=str(tmp_path / "Business")))

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.INCOMPLETE_CONFIGURATION
    assert assessment.data_root == tmp_path / "Business"
    assert assessment.database is None


def test_healthy_database_is_ready(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    try:
        assert assessment.mode is StartupMode.READY
        assert assessment.is_ready
        assert assessment.database is not None
        assert assessment.database.config.path == database_path
        assert assessment.database_path == database_path
        assert assessment.data_root == data_root
    finally:
        assert assessment.database is not None
        assessment.database.shutdown()


def test_legacy_configuration_without_data_root_is_ready(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    database_path = tmp_path / "Business" / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    _configure(config_service, None, database_path)

    assessment = StartupService(config_service).assess()

    try:
        assert assessment.mode is StartupMode.READY
        assert assessment.data_root is None
        assert assessment.database is not None
    finally:
        assert assessment.database is not None
        assessment.database.shutdown()


def test_missing_drive_blocks_startup_without_creating_a_database(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = Path(_missing_drive()) / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.MISSING_DRIVE
    assert assessment.database is None
    assert not database_path.exists()
    assert not (tmp_path / "Business").exists()


def test_missing_data_folder_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    data_root.mkdir()
    database_path = data_root / "Database" / "BusinessManagement.db"
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.MISSING_FOLDER
    assert not database_path.exists()


def test_missing_database_file_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.MISSING_DATABASE
    assert not database_path.exists()
    assert "No replacement database was created" in assessment.message


def test_directory_at_database_path_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    database_path.mkdir(parents=True)
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.INVALID_LOCATION
    assert assessment.database is None


def test_unc_configuration_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    config_service.config_path.parent.mkdir(parents=True)
    payload = {
        "schema_version": 1,
        "data_root": r"\\server\share\Business",
        "database_path": r"\\server\share\Business\Database\BusinessManagement.db",
    }
    config_service.config_path.write_text(json.dumps(payload), encoding="utf-8")

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.INVALID_LOCATION
    assert assessment.database is None


def test_corrupt_database_is_refused_without_modification(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    original = b"not sqlite" * 32
    database_path.write_bytes(original)
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.database is None
    assert database_path.read_bytes() == original


def test_uninitialized_database_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    database_path.write_bytes(b"")
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.MIGRATION_REQUIRED
    assert assessment.database is None


def test_newer_schema_requires_recovery(tmp_path: Path) -> None:
    config_service = _config_service(tmp_path)
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE alembic_version SET version_num = '9999_future'")
    _configure(config_service, data_root, database_path)

    assessment = StartupService(config_service).assess()

    assert assessment.mode is StartupMode.RECOVERY_REQUIRED
    assert assessment.recovery_reason is RecoveryReason.MIGRATION_UNSUPPORTED
    assert assessment.database is None
