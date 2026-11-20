"""Business Profile UI and main-window integration tests (offscreen)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from app.core.config import AppConfig, ConfigService
from app.infrastructure.database.engine import Database
from app.services.business_profile_service import BusinessProfileServiceFactory
from app.services.database_runtime import DatabaseRuntime
from app.ui.main_window import MainWindow
from app.ui.themes.manager import ThemeManager
from app.ui.viewmodels.business_profile_viewmodel import BusinessProfileViewModel
from app.ui.viewmodels.shell_viewmodel import ShellViewModel
from app.ui.views.business_profile_view import BusinessProfileView


def clock() -> str:
    return "2026-11-20T10:30:00Z"


def _save_config(config_service: ConfigService, root: Path, database: Database) -> None:
    config_service.save(
        AppConfig().with_database_location(
            data_root=root, database_path=database.config.path
        )
    )


@pytest.fixture
def profile_view(
    qapp,
    initialized_database: Database,
    profile_data_root: Path,
    config_service: ConfigService,
):
    _save_config(config_service, profile_data_root, initialized_database)
    runtime = DatabaseRuntime(initialized_database)
    factory = BusinessProfileServiceFactory(config_service, runtime, clock=clock)
    viewmodel = BusinessProfileViewModel(factory)
    view = BusinessProfileView(viewmodel)
    view.show()
    qapp.processEvents()
    yield view
    view.close()
    view.deleteLater()
    qapp.processEvents()


def _complete_form(view: BusinessProfileView, logo_path: Path) -> None:
    view.field_edit("business_name").setText("Gobindas Graphics")
    view.field_edit("address").setText("Sector 1")
    view.field_edit("phone").setText("9876543210")
    view.field_edit("email").setText("office@example.com")
    view.field_edit("footer_message").setText("Thank you")
    view.set_logo_path(logo_path)


def test_empty_profile_shows_guided_empty_state(profile_view: BusinessProfileView) -> None:
    assert profile_view.empty_state.isVisible()
    assert profile_view.status_badge.tone == "info"
    assert "No business profile yet" in profile_view.status_badge.text()
    assert profile_view.reset_button.isEnabled() is False
    assert profile_view.save_button.isEnabled() is True
    assert profile_view.history_list.count() == 0


def test_valid_save_updates_status_empty_state_and_history(
    profile_view: BusinessProfileView, logo_file: Path
) -> None:
    _complete_form(profile_view, logo_file)

    profile_view.save_button.click()

    assert profile_view.viewmodel.snapshot is not None
    assert profile_view.viewmodel.snapshot.profile is not None
    assert profile_view.viewmodel.snapshot.profile.business_name == "Gobindas Graphics"
    assert profile_view.viewmodel.snapshot.profile.logo_reference.startswith("Logos/")
    assert profile_view.status_badge.tone == "pass"
    assert "Complete" in profile_view.status_badge.text()
    assert profile_view.empty_state.isVisible() is False
    assert profile_view.reset_button.isEnabled() is False
    assert profile_view.history_list.count() == 1
    assert "Version 1" in profile_view.history_list.item(0).text()


def test_invalid_save_shows_inline_errors_without_modal_dialog(
    profile_view: BusinessProfileView,
) -> None:
    profile_view.save_button.click()

    assert "Business name is required." in profile_view.error_label("business_name").text()
    assert profile_view.error_label("business_name").isVisible()
    assert "business logo is required" in profile_view.error_label("logo").text()
    assert profile_view.error_label("logo").isVisible()
    assert profile_view.error_label("business_name").accessibleName().startswith("Error:")
    assert profile_view.findChildren(QMessageBox) == []
    assert profile_view.status_badge.tone == "error"


def test_reset_discards_unsaved_changes(
    profile_view: BusinessProfileView, logo_file: Path
) -> None:
    _complete_form(profile_view, logo_file)
    profile_view.save_button.click()
    profile_view.field_edit("business_name").setText("Temporary name")
    assert profile_view.reset_button.isEnabled() is True

    profile_view.reset_button.click()

    assert profile_view.field_edit("business_name").text() == "Gobindas Graphics"
    assert profile_view.reset_button.isEnabled() is False
    assert profile_view.viewmodel.snapshot is not None
    assert profile_view.viewmodel.snapshot.pending_logo_path is None


def test_history_selection_loads_a_previous_version(
    profile_view: BusinessProfileView, logo_file: Path
) -> None:
    _complete_form(profile_view, logo_file)
    profile_view.save_button.click()
    profile_view.field_edit("business_name").setText("Version Two")
    profile_view.save_button.click()
    assert profile_view.history_list.count() == 2

    profile_view.viewmodel.select_version(1)

    assert profile_view.field_edit("business_name").text() == "Gobindas Graphics"
    assert profile_view.viewmodel.snapshot is not None
    assert profile_view.viewmodel.snapshot.selected_version == 1
    assert "Showing profile version 1" in profile_view.status_badge.text()


def test_missing_database_is_reported_without_disabled_form(
    qapp, config_service: ConfigService
) -> None:
    factory = BusinessProfileServiceFactory(config_service, DatabaseRuntime())
    viewmodel = BusinessProfileViewModel(factory)
    view = BusinessProfileView(viewmodel)
    view.show()
    qapp.processEvents()
    try:
        assert view.status_badge.tone == "warning"
        assert "No business database and data root" in view.status_badge.text()
        assert view.empty_state.isVisible() is True
        assert view.save_button.isEnabled() is False
        assert view.field_edit("business_name").isEnabled() is False
    finally:
        view.close()
        view.deleteLater()
        qapp.processEvents()


def test_settings_navigation_opens_business_profile(
    qapp,
    config_service: ConfigService,
    initialized_database: Database,
    profile_data_root: Path,
    tmp_path,
) -> None:
    _save_config(config_service, profile_data_root, initialized_database)
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    factory = BusinessProfileServiceFactory(
        config_service, DatabaseRuntime(initialized_database), clock=clock
    )
    window = MainWindow(
        ShellViewModel(config_service, config_service.load()),
        ThemeManager(qapp),
        database_runtime=DatabaseRuntime(initialized_database),
        business_profile_factory=factory,
        settings=settings,
    )
    try:
        window.navigate("settings")

        view = window.content_stack.currentWidget()
        assert isinstance(view, BusinessProfileView)
        assert window.top_bar.title_label.text() == "Settings"
        assert "Business profile" in window.top_bar.subtitle_label.text()
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
