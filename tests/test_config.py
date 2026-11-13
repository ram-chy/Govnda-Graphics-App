"""Configuration loading, validation, and atomic persistence tests."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.core import constants
from app.core.config import AppConfig, ConfigService
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
