"""Main window and theme switching tests (offscreen)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel

from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.ui.components.placeholder_view import PlaceholderView
from app.ui.main_window import MainWindow
from app.ui.themes.manager import ThemeManager, ThemeMode
from app.ui.themes.tokens import DARK_PALETTE, LIGHT_PALETTE
from app.ui.viewmodels.shell_viewmodel import ShellViewModel


@pytest.fixture
def window(qapp, config_service: ConfigService) -> MainWindow:
    config = AppConfig(theme="light")
    config_service.save(config)
    viewmodel = ShellViewModel(config_service, config)
    theme_manager = ThemeManager(qapp)
    main_window = MainWindow(viewmodel, theme_manager)
    yield main_window
    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


def _label_texts(window: MainWindow) -> list[str]:
    return [label.text() for label in window.findChildren(QLabel)]


def test_window_title_and_minimum_size(window: MainWindow) -> None:
    assert window.windowTitle() == constants.APP_NAME
    assert window.minimumWidth() == 1280
    assert window.minimumHeight() == 720


def test_navigation_entries_and_default_view(window: MainWindow) -> None:
    assert window.sidebar.keys == (
        "dashboard",
        "sales",
        "purchases",
        "inventory",
        "customers",
        "suppliers",
        "expenses",
        "accounting",
        "reports",
        "settings",
        "backup",
    )
    assert window.current_key == "dashboard"
    assert window.top_bar.title_label.text() == "Dashboard"
    assert window.sidebar.button("dashboard").isChecked() is True


def test_status_bar_shows_foundation_state(window: MainWindow) -> None:
    texts = _label_texts(window)

    assert "Database: not configured" in texts
    assert "INR \u20b9" in texts
    assert "Local only" in texts
    assert f"v{constants.APP_VERSION}" in texts


def test_home_view_shows_inr_format_example(window: MainWindow) -> None:
    texts = _label_texts(window)

    assert any("\u20b91,250.50" in text for text in texts)
    assert "INR  \u20b9" in texts


def test_navigation_creates_placeholder_lazily(window: MainWindow) -> None:
    assert window.content_stack.count() == 1

    window.navigate("sales")

    assert window.current_key == "sales"
    assert window.top_bar.title_label.text() == "Sales"
    assert window.sidebar.button("sales").isChecked() is True
    assert window.content_stack.count() == 2
    view = window.content_stack.currentWidget()
    assert isinstance(view, PlaceholderView)
    assert any(label.text() == "Sales is not available yet" for label in view.findChildren(QLabel))


def test_view_instance_is_reused(window: MainWindow) -> None:
    window.navigate("sales")
    first = window.content_stack.currentWidget()
    window.navigate("reports")
    window.navigate("sales")

    assert window.content_stack.currentWidget() is first
    assert window.content_stack.count() == 3


def test_unknown_navigation_key_raises(window: MainWindow) -> None:
    with pytest.raises(KeyError):
        window.navigate("payroll")


def test_theme_toggle_applies_and_persists(
    window: MainWindow, qapp, config_service: ConfigService
) -> None:
    assert window.theme_manager.is_dark is False
    assert window.top_bar.theme_button.text() == "Dark mode"

    window.top_bar.theme_button.click()

    assert window.theme_manager.is_dark is True
    assert window.theme_manager.preference is ThemeMode.DARK
    assert window.top_bar.theme_button.text() == "Light mode"
    assert DARK_PALETTE.bg_app in qapp.styleSheet()
    assert config_service.load().theme == "dark"

    window.top_bar.theme_button.click()

    assert window.theme_manager.is_dark is False
    assert LIGHT_PALETTE.bg_app in qapp.styleSheet()
    assert config_service.load().theme == "light"


def test_theme_manager_apply_validates_preference(qapp) -> None:
    manager = ThemeManager(qapp)

    manager.apply("dark")
    assert manager.is_dark is True
    assert manager.preference is ThemeMode.DARK

    manager.apply(ThemeMode.LIGHT)
    assert manager.is_dark is False

    with pytest.raises(ValueError):
        manager.apply("neon")


def test_theme_manager_toggle_switches_between_explicit_themes(qapp) -> None:
    manager = ThemeManager(qapp)
    manager.apply("light")

    assert manager.toggle() is ThemeMode.DARK
    assert manager.toggle() is ThemeMode.LIGHT


def test_configured_database_is_reported_in_status_and_home(
    qapp, config_service: ConfigService, tmp_path
) -> None:
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    config = AppConfig(
        theme="light",
        data_root=str(root),
        database_path=str(database_path),
    )
    config_service.save(config)
    viewmodel = ShellViewModel(config_service, config)
    window = MainWindow(
        viewmodel,
        ThemeManager(qapp),
        database_path=database_path,
        data_root=root,
    )

    try:
        labels = window.findChildren(QLabel)
        texts = [label.text() for label in labels]
        assert "Database: configured" in texts
        configured = next(label for label in labels if label.text() == "Database: configured")
        assert configured.toolTip() == str(database_path)
        assert any(str(database_path) in text for text in texts)
        assert any(text == str(root) for text in texts)
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
