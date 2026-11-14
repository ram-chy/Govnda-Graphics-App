"""Configuration loading, validation, and atomic persistence tests."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.core import constants
from app.core.config import AppConfig, ConfigLoadStatus, ConfigService
from app.core.exceptions import ConfigurationError
from app.core.formatting import format_money


def test_missing_file_returns_defaults_without_creating_it(config_service: ConfigService) -> None:
    config = config_service.load()

    assert config == AppConfig()
    assert not config_service.config_path.exists()


def test_default_config_uses_inr(config_service: ConfigService) -> None:
    config = config_service.load()

    assert config.schema_version == constants.CONFIG_SCHEMA_VERSION
    assert config.currency_code == "INR"
    assert config.currency_symbol == "\u20b9"
    assert config.currency_decimal_places == 2
    assert config.currency_grouping == "indian"
    assert config.theme == "system"
    assert config.app_name == constants.APP_NAME
    assert config.app_version == constants.APP_VERSION
    assert format_money(Decimal("1250.50"), config.currency) == "\u20b91,250.50"


def test_save_and_load_round_trip(config_service: ConfigService) -> None:
    config = AppConfig(theme="dark")

    config_service.save(config)
    loaded = config_service.load()

    assert loaded == config
    assert config_service.config_path.exists()


def test_saved_file_is_utf8_and_contains_no_temporary_files(
    config_service: ConfigService,
) -> None:
    config_service.save(AppConfig())

    text = config_service.config_path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["currency_symbol"] == "\u20b9"
    assert payload["currency_code"] == "INR"
    assert payload["theme"] == "system"
    assert "\u20b9" in text
    leftovers = [
        path for path in config_service.config_path.parent.iterdir() if path.suffix == ".tmp"
    ]
    assert leftovers == []


def test_save_creates_parent_directories(config_service: ConfigService) -> None:
    assert not config_service.config_path.parent.exists()

    config_service.save(AppConfig())

    assert config_service.config_path.parent.is_dir()


def test_unknown_keys_are_ignored(config_service: ConfigService) -> None:
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text(
        json.dumps({"theme": "light", "future_setting": "value"}), encoding="utf-8"
    )

    config = config_service.load()

    assert config.theme == "light"
    assert not hasattr(config, "future_setting")


def test_currency_property_reflects_configuration() -> None:
    config = AppConfig(
        currency_code="INR",
        currency_symbol="\u20b9",
        currency_decimal_places=2,
        currency_grouping="indian",
    )

    currency = config.currency

    assert currency.code == "INR"
    assert currency.symbol == "\u20b9"
    assert currency.decimal_places == 2


def test_with_theme_returns_validated_copy() -> None:
    config = AppConfig(theme="light")

    updated = config.with_theme("dark")

    assert updated.theme == "dark"
    assert config.theme == "light"
    with pytest.raises(ConfigurationError):
        config.with_theme("neon")


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 2},
        {"currency_code": "inr"},
        {"currency_code": "IN"},
        {"currency_symbol": ""},
        {"currency_decimal_places": 5},
        {"currency_decimal_places": -1},
        {"currency_decimal_places": True},
        {"currency_grouping": "european"},
        {"theme": "neon"},
        {"log_level": "TRACE"},
    ],
)
def test_invalid_config_values_are_rejected(changes: dict[str, object]) -> None:
    config = replace(AppConfig(), **changes)  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError):
        config.validate()


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        '"string"',
        json.dumps({"theme": "neon"}),
        json.dumps({"currency_decimal_places": "two"}),
        json.dumps({"currency_code": "INR", "schema_version": 2}),
        json.dumps({"currency_symbol": None}),
    ],
)
def test_invalid_file_is_preserved_and_defaults_are_used(
    config_service: ConfigService, payload: str
) -> None:
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text(payload, encoding="utf-8")

    config = config_service.load()

    assert config == AppConfig()
    assert not config_service.config_path.exists()
    corrupt_files = list(config_service.config_path.parent.glob("config.corrupt-*.json"))
    assert len(corrupt_files) == 1
    assert corrupt_files[0].read_text(encoding="utf-8") == payload


def test_save_failure_preserves_existing_file(
    config_service: ConfigService, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_service.save(AppConfig(theme="light"))
    original = config_service.config_path.read_text(encoding="utf-8")

    def failing_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("app.core.config.os.replace", failing_replace)

    with pytest.raises(ConfigurationError):
        config_service.save(AppConfig(theme="dark"))

    assert config_service.config_path.read_text(encoding="utf-8") == original
    leftovers = [
        path for path in config_service.config_path.parent.iterdir() if path.suffix == ".tmp"
    ]
    assert leftovers == []


def test_saving_invalid_config_does_not_touch_file(config_service: ConfigService) -> None:
    config_service.save(AppConfig(theme="light"))
    original = config_service.config_path.read_text(encoding="utf-8")
    invalid = replace(AppConfig(), theme="neon")

    with pytest.raises(ConfigurationError):
        config_service.save(invalid)

    assert config_service.config_path.read_text(encoding="utf-8") == original


def test_database_path_defaults_to_none() -> None:
    assert AppConfig().database_path is None


def test_absolute_database_path_is_accepted_and_round_trips(
    config_service: ConfigService, tmp_path: Path
) -> None:
    database_path = tmp_path / "data" / "gobindas.db"
    config_service.save(AppConfig(database_path=str(database_path)))

    loaded = config_service.load()

    assert loaded.database_path == str(database_path)
    assert loaded == AppConfig(database_path=str(database_path))


def test_relative_database_path_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="absolute"):
        AppConfig(database_path="data/gobindas.db").validate()


def test_blank_database_path_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="non-empty"):
        AppConfig(database_path="   ").validate()


def test_null_database_path_in_json_is_accepted(config_service: ConfigService) -> None:
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text('{"schema_version": 1, "database_path": null}')

    assert config_service.load().database_path is None


def test_data_root_and_database_path_round_trip(
    config_service: ConfigService, tmp_path: Path
) -> None:
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    config = AppConfig(
        theme="light",
        data_root=str(root),
        database_path=str(database_path),
    )

    config_service.save(config)
    loaded = config_service.load()

    assert loaded == config
    assert loaded.data_root == str(root)
    assert loaded.database_path == str(database_path)
    assert loaded.currency_code == "INR"
    assert loaded.currency_symbol == "\u20b9"
    assert loaded.currency_decimal_places == 2


def test_legacy_config_with_only_database_path_remains_valid(
    config_service: ConfigService, tmp_path: Path
) -> None:
    database_path = tmp_path / "data" / "legacy.db"
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text(
        json.dumps({"schema_version": 1, "database_path": str(database_path)}),
        encoding="utf-8",
    )

    result = config_service.load_with_status()

    assert result.status is ConfigLoadStatus.LOADED
    assert result.config.database_path == str(database_path)
    assert result.config.data_root is None


def test_null_data_root_in_json_is_accepted(config_service: ConfigService) -> None:
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text('{"schema_version": 1, "data_root": null}')

    assert config_service.load().data_root is None


def test_load_with_status_reports_missing_without_creating_the_file(
    config_service: ConfigService,
) -> None:
    result = config_service.load_with_status()

    assert result.status is ConfigLoadStatus.MISSING
    assert result.config == AppConfig()
    assert result.quarantined_path is None
    assert not config_service.config_path.exists()


def test_load_with_status_reports_a_loaded_file(
    config_service: ConfigService,
) -> None:
    config_service.save(AppConfig(theme="light"))

    result = config_service.load_with_status()

    assert result.status is ConfigLoadStatus.LOADED
    assert result.config.theme == "light"
    assert result.quarantined_path is None


def test_load_with_status_reports_recovered_configuration(
    config_service: ConfigService,
) -> None:
    config_service.config_path.parent.mkdir(parents=True)
    config_service.config_path.write_text('{"theme": "neon"}', encoding="utf-8")

    result = config_service.load_with_status()

    assert result.status is ConfigLoadStatus.RECOVERED
    assert result.config == AppConfig()
    assert result.quarantined_path is not None
    assert result.quarantined_path.is_file()
    assert result.quarantined_path.read_text(encoding="utf-8") == '{"theme": "neon"}'
    assert not config_service.config_path.exists()


def test_database_path_outside_data_root_is_rejected(tmp_path: Path) -> None:
    config = AppConfig(
        data_root=str(tmp_path / "Business"),
        database_path=str(tmp_path / "Elsewhere" / "BusinessManagement.db"),
    )

    with pytest.raises(ConfigurationError, match="inside data_root"):
        config.validate()


def test_with_database_location_preserves_existing_settings(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    config = AppConfig(theme="dark", log_level="DEBUG")

    updated = config.with_database_location(data_root=root, database_path=database_path)

    assert updated.data_root == str(root)
    assert updated.database_path == str(database_path)
    assert updated.theme == "dark"
    assert updated.log_level == "DEBUG"
    assert updated.currency_code == "INR"
    assert updated.currency_symbol == "\u20b9"
    assert config.data_root is None
    assert config.database_path is None


def test_with_database_location_rejects_a_database_outside_the_root(
    tmp_path: Path,
) -> None:
    config = AppConfig()

    with pytest.raises(ConfigurationError, match="inside data_root"):
        config.with_database_location(
            data_root=tmp_path / "Business",
            database_path=tmp_path / "Outside" / "BusinessManagement.db",
        )


def test_relative_data_root_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="absolute"):
        AppConfig(data_root="Business").validate()


def test_blank_data_root_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="non-empty"):
        AppConfig(data_root="   ").validate()
