"""Native setup wizard navigation, cancellation, and worker integration."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog

from app.core.config import AppConfig, ConfigService
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager
from app.infrastructure.filesystem.drives import DriveInfo, DriveType
from app.infrastructure.filesystem.validation import DataLocationValidator
from app.services.setup_service import SetupService
from app.ui.dialogs.setup_wizard import (
    PAGE_COMPLETION,
    PAGE_CONFIRM,
    PAGE_LOCATION,
    PAGE_PROGRESS,
    PAGE_REVIEW,
    PAGE_VALIDATION,
    PAGE_WELCOME,
    SetupWizard,
)


def _service(tmp_path: Path) -> SetupService:
    def provider(root: Path) -> DriveInfo:
        return DriveInfo(
            root=Path(root),
            drive_type=DriveType.FIXED,
            label="Test volume",
            filesystem="NTFS",
            total_bytes=10 * 1024**3,
            free_bytes=10 * 1024**3,
        )

    validator = DataLocationValidator(
        installation_dirs=[],
        protected_dirs=[],
        drive_info_provider=provider,
        write_probe=lambda _path: None,
    )
    return SetupService(
        ConfigService(tmp_path / "config" / "config.json"), validator=validator
    )


def _wizard(tmp_path: Path) -> SetupWizard:
    return SetupWizard(_service(tmp_path), AppConfig())


def _wait_until(predicate, timeout_ms: int = 90_000) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if predicate():
            return True
        QApplication.processEvents()
        time.sleep(0.02)
    return False


def _create_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(DatabaseConfig(path=database_path))
    try:
        MigrationManager(database).create_database()
    finally:
        database.shutdown()


def test_wizard_starts_on_welcome_and_hides_back(qapp, tmp_path: Path) -> None:
    wizard = _wizard(tmp_path)

    try:
        assert wizard.current_page == PAGE_WELCOME
        assert not wizard._back_button.isVisible() or not wizard.isVisible()
        assert wizard._next_button.text() == "Get started"
    finally:
        wizard.reject()


def test_wizard_navigation_reaches_confirmation(qapp, tmp_path: Path) -> None:
    wizard = _wizard(tmp_path)
    root = tmp_path / "Business"

    try:
        wizard._next_button.click()
        assert wizard.current_page == PAGE_LOCATION
        assert not wizard._next_button.isEnabled()

        wizard._path_edit.setText(str(root))
        assert wizard._next_button.isEnabled()
        wizard._next_button.click()
        assert wizard.current_page == PAGE_VALIDATION
        assert wizard._viewmodel.can_continue
        assert wizard._next_button.isEnabled()

        wizard._next_button.click()
        assert wizard.current_page == PAGE_REVIEW
        assert wizard._review_tree.topLevelItemCount() > 0
        assert str(root) in wizard._review_database.text()

        wizard._next_button.click()
        assert wizard.current_page == PAGE_CONFIRM
        assert not wizard._confirm_checkbox.isChecked()
        assert not wizard._next_button.isEnabled()
        wizard._confirm_checkbox.setChecked(True)
        assert wizard._next_button.isEnabled()
        assert wizard._next_button.text() == "Create database"

        wizard._back_button.click()
        assert wizard.current_page == PAGE_REVIEW
        wizard._back_button.click()
        assert wizard.current_page == PAGE_VALIDATION
    finally:
        wizard.reject()


def test_invalid_location_cannot_continue(qapp, tmp_path: Path) -> None:
    wizard = _wizard(tmp_path)

    try:
        wizard._next_button.click()
        wizard._path_edit.setText("relative/Business")
        wizard._next_button.click()

        assert wizard.current_page == PAGE_VALIDATION
        assert not wizard._viewmodel.can_continue
        assert not wizard._next_button.isEnabled()
        wizard._next_button.click()
        assert wizard.current_page == PAGE_VALIDATION
    finally:
        wizard.reject()


def test_existing_database_uses_the_safe_connect_wording(qapp, tmp_path: Path) -> None:
    root = tmp_path / "Business"
    _create_database(root / "Database" / "BusinessManagement.db")
    wizard = _wizard(tmp_path)

    try:
        wizard._next_button.click()
        wizard._path_edit.setText(str(root))
        wizard._next_button.click()
        wizard._next_button.click()
        wizard._next_button.click()

        assert wizard.current_page == PAGE_CONFIRM
        assert wizard._next_button.text() == "Connect to existing database"
        assert "verify" in wizard._confirm_checkbox.text()
    finally:
        wizard.reject()


def test_cancelled_setup_creates_no_database_or_configuration(qapp, tmp_path: Path) -> None:
    wizard = _wizard(tmp_path)

    wizard.reject()

    assert wizard.take_result() is None
    assert not (tmp_path / "Business").exists()
    assert not (tmp_path / "config" / "config.json").exists()


def test_successful_setup_reaches_completion_and_hands_off_result(
    qapp, tmp_path: Path
) -> None:
    service = _service(tmp_path)
    wizard = SetupWizard(service, AppConfig())
    root = tmp_path / "Business"

    try:
        wizard.show()
        wizard._next_button.click()
        wizard._path_edit.setText(str(root))
        wizard._next_button.click()
        wizard._next_button.click()
        wizard._next_button.click()
        wizard._confirm_checkbox.setChecked(True)
        wizard._next_button.click()

        assert wizard.is_busy
        assert wizard.current_page == PAGE_PROGRESS

        completed = _wait_until(
            lambda: wizard.current_page == PAGE_COMPLETION and not wizard.is_busy
        )
        assert completed, wizard._progress_status.text()
        assert _wait_until(lambda: wizard._thread is None)

        wizard._next_button.click()
        assert wizard.result() == QDialog.DialogCode.Accepted

        result = wizard.take_result()
        assert result is not None
        try:
            assert result.database_path.is_file()
            assert result.health.healthy
            assert result.adopted_existing_database is False
            saved = service._config_service.load()  # noqa: SLF001 - test verification
            assert saved.data_root == str(root)
            assert saved.database_path == str(result.database_path)
            assert saved.currency_code == "INR"
        finally:
            result.database.shutdown()
    finally:
        wizard.close()


def test_wizard_worker_failure_shows_choose_another_folder(qapp, tmp_path: Path) -> None:
    root = tmp_path / "Business"
    root.mkdir()
    blocker = root / "Database"
    blocker.write_text("a file blocks the folder", encoding="utf-8")
    wizard = _wizard(tmp_path)

    try:
        wizard.show()
        wizard._next_button.click()
        wizard._path_edit.setText(str(root))
        wizard._next_button.click()
        wizard._next_button.click()
        wizard._next_button.click()
        wizard._confirm_checkbox.setChecked(True)
        wizard._next_button.click()

        assert _wait_until(lambda: not wizard.is_busy and wizard._thread is None)
        assert wizard.current_page == PAGE_PROGRESS
        assert not wizard._failure_label.isHidden()
        assert not wizard._choose_location_button.isHidden()
        assert blocker.read_text(encoding="utf-8") == "a file blocks the folder"

        wizard._choose_location_button.click()
        assert wizard.current_page == PAGE_LOCATION
    finally:
        wizard.close()
