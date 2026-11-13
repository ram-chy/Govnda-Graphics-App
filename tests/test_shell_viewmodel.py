"""Shell view model tests - no widgets required."""

from __future__ import annotations

import pytest

from app.core.config import AppConfig, ConfigService
from app.core.exceptions import ConfigurationError
from app.ui.viewmodels.shell_viewmodel import ShellViewModel


def test_initial_state(config_service: ConfigService, qapp) -> None:
    config = AppConfig(theme="light")
    viewmodel = ShellViewModel(config_service, config)

    assert viewmodel.theme_preference == "light"
    assert viewmodel.currency.code == "INR"
    assert viewmodel.currency.symbol == "\u20b9"
    assert viewmodel.app_version == config.app_version


def test_theme_preference_is_persisted(config_service: ConfigService, qapp) -> None:
    config = AppConfig(theme="light")
    viewmodel = ShellViewModel(config_service, config)
    emitted: list[str] = []
    statuses: list[str] = []
    viewmodel.theme_preference_changed.connect(emitted.append)
    viewmodel.status_message_changed.connect(statuses.append)

    assert viewmodel.set_theme_preference("dark") is True

    assert viewmodel.theme_preference == "dark"
    assert emitted == ["dark"]
    assert config_service.load().theme == "dark"
    assert statuses == ["Theme preference saved: Dark."]


def test_invalid_theme_is_rejected(config_service: ConfigService, qapp) -> None:
    viewmodel = ShellViewModel(config_service, AppConfig(theme="light"))
    statuses: list[str] = []
    viewmodel.status_message_changed.connect(statuses.append)

    assert viewmodel.set_theme_preference("neon") is False

    assert viewmodel.theme_preference == "light"
    assert statuses == ["The selected theme is not supported."]
    assert not config_service.config_path.exists()


def test_save_failure_keeps_session_usable(
    config_service: ConfigService, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = AppConfig(theme="light")
    viewmodel = ShellViewModel(config_service, config)
    statuses: list[str] = []
    viewmodel.status_message_changed.connect(statuses.append)

    def failing_save(_config: AppConfig) -> None:
        raise ConfigurationError("disk full")

    monkeypatch.setattr(config_service, "save", failing_save)

    assert viewmodel.set_theme_preference("dark") is False

    assert viewmodel.theme_preference == "light"
    assert statuses == ["The theme changed for this session but could not be saved."]
