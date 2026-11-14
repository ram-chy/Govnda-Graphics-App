"""Setup orchestration: validation, scaffolding, initialization, persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.core.config import AppConfig, ConfigService
from app.core.exceptions import ConfigurationError, SetupError
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager
from app.infrastructure.filesystem.drives import DriveInfo, DriveType
from app.infrastructure.filesystem.validation import DataLocationValidator
from app.services.setup_service import SetupPersistenceError, SetupResult, SetupService


def _validator() -> DataLocationValidator:
    def provider(root: Path) -> DriveInfo:
        return DriveInfo(
            root=Path(root),
            drive_type=DriveType.FIXED,
            label="Test volume",
            filesystem="NTFS",
            total_bytes=10 * 1024**3,
            free_bytes=10 * 1024**3,
        )

    return DataLocationValidator(
        installation_dirs=[],
        protected_dirs=[],
        drive_info_provider=provider,
        write_probe=lambda _path: None,
    )


def _service(config_service: ConfigService) -> SetupService:
    return SetupService(config_service, validator=_validator())


def _create_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(DatabaseConfig(path=database_path))
    try:
        MigrationManager(database).create_database()
    finally:
        database.shutdown()


def _close(result: SetupResult) -> None:
    result.database.shutdown()


def test_initialize_creates_database_directories_and_configuration(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    root = tmp_path / "Business"

    result = service.initialize(root, base_config=AppConfig())

    try:
        assert not result.adopted_existing_database
        assert result.data_root == root
        assert result.database_path.is_file()
        assert result.migration.current_revision == "0001_baseline"
        assert result.health.healthy
        for directory in result.layout.required_directories():
            assert directory.is_dir()

        saved = config_service.load()
        assert saved.data_root == str(root)
        assert saved.database_path == str(result.database_path)
        assert saved.currency_code == "INR"
        assert saved.currency_symbol == "\u20b9"
        assert saved.currency_decimal_places == 2
        assert saved.currency_grouping == "indian"
    finally:
        _close(result)


def test_existing_application_settings_are_preserved(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    base = AppConfig(theme="dark", log_level="DEBUG")
    service = _service(config_service)

    result = service.initialize(tmp_path / "Business", base_config=base)

    try:
        saved = config_service.load()
        assert saved.theme == "dark"
        assert saved.log_level == "DEBUG"
        assert saved.currency_code == "INR"
        assert saved.data_root is not None
        assert saved.database_path is not None
    finally:
        _close(result)


def test_existing_healthy_database_is_adopted_without_overwriting(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    sentinel = database_path.parent / "existing-note.txt"
    sentinel.write_text("keep", encoding="utf-8")

    result = service.initialize(root, base_config=AppConfig())

    try:
        assert result.adopted_existing_database
        assert result.database_path == database_path
        assert result.migration.current_revision == "0001_baseline"
        assert sentinel.read_text(encoding="utf-8") == "keep"
    finally:
        _close(result)


def test_existing_uninitialized_database_is_refused(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER)")

    with pytest.raises(SetupError):
        service.initialize(root, base_config=AppConfig())

    assert database_path.is_file()
    assert not config_service.config_path.exists()


def test_corrupt_database_is_refused_without_being_modified(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    original = b"not a database" * 64
    database_path.write_bytes(original)

    with pytest.raises(SetupError):
        service.initialize(root, base_config=AppConfig())

    assert database_path.read_bytes() == original
    assert not config_service.config_path.exists()


def test_attach_existing_refuses_to_create_a_database(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    root = tmp_path / "Missing"

    with pytest.raises(SetupError, match="no existing database"):
        service.attach_existing(root, base_config=AppConfig())

    assert not root.exists()
    assert not config_service.config_path.exists()


def test_attach_existing_adopts_a_healthy_database(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    _create_database(database_path)

    result = service.attach_existing(root, base_config=AppConfig())

    try:
        assert result.adopted_existing_database
        assert result.migration.current_revision == "0001_baseline"
        assert config_service.load().database_path == str(database_path)
    finally:
        _close(result)


def test_invalid_location_is_rejected_before_creating_anything(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)

    with pytest.raises(SetupError):
        service.initialize("relative/Business", base_config=AppConfig())

    assert not (tmp_path / "relative").exists()
    assert not config_service.config_path.exists()


def test_progress_callback_receives_each_stage(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    messages: list[str] = []

    result = service.initialize(
        tmp_path / "Business", base_config=AppConfig(), progress=messages.append
    )

    try:
        assert messages == [
            "Checking the selected folder",
            "Preparing the database",
            "Verifying database integrity",
            "Saving the data location",
        ]
    finally:
        _close(result)


def test_failed_configuration_persistence_is_recoverable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)
    original_save = config_service.save
    state = {"fail": True}

    def controlled_save(config: AppConfig) -> None:
        if state["fail"]:
            raise ConfigurationError("simulated configuration failure")
        original_save(config)

    monkeypatch.setattr(config_service, "save", controlled_save)

    with pytest.raises(SetupPersistenceError) as excinfo:
        service.initialize(tmp_path / "Business", base_config=AppConfig())

    pending = excinfo.value.result
    try:
        assert pending.database_path.is_file()
        assert pending.database.config.path == pending.database_path
        assert not config_service.config_path.exists()
    finally:
        pending.database.shutdown()

    state["fail"] = False
    retried = service.persist(pending)
    try:
        assert retried.data_root == str(tmp_path / "Business")
        assert config_service.load().database_path == str(pending.database_path)
    finally:
        pending.database.shutdown()


def test_validation_is_exposed_without_side_effects(tmp_path: Path) -> None:
    config_service = ConfigService(tmp_path / "config" / "config.json")
    service = _service(config_service)

    result = service.validate(tmp_path / "Business")

    assert result.is_valid
    assert not (tmp_path / "Business").exists()
    assert not config_service.config_path.exists()
