"""Phase 5 UI refinement tests (offscreen Qt).

These tests verify programmatic structure, tokens, feedback states, keyboard
hooks, and persistence. They do not claim visual or Windows DPI verification.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QKeySequence, QPalette, QShortcut
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from app.core.config import AppConfig, ConfigService
from app.core.exceptions import AppError
from app.domain.backup import BackupRecord, BackupStatus, BackupType
from app.infrastructure.backup.state import BackupState
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager
from app.services.schedule_service import BackupSettings
from app.ui.components.controls import DetailCard, make_button, set_dialog_size
from app.ui.components.feedback import (
    EmptyState,
    StatusBadge,
    Toast,
    apply_status,
    show_toast,
)
from app.ui.dialogs.backup_settings_dialog import BackupSettingsDialog
from app.ui.dialogs.recovery_dialog import RecoveryAction, RecoveryDialog
from app.ui.dialogs.restore_confirmation_dialog import RestoreConfirmationDialog
from app.ui.main_window import MainWindow
from app.ui.themes.manager import ThemeManager
from app.ui.themes.qss import build_stylesheet
from app.ui.themes.tokens import (
    DARK_CHART_PALETTE,
    DARK_PALETTE,
    LIGHT_CHART_PALETTE,
    LIGHT_PALETTE,
)
from app.ui.viewmodels.backup_viewmodel import BackupSnapshot, BackupViewModel
from app.ui.viewmodels.shell_viewmodel import ShellViewModel
from app.ui.viewmodels.task_runner import InlineTaskRunner
from app.ui.views.backup_view import BackupView

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeBackupViewModel(QObject):
    """Signal-compatible stand-in for testing the view in isolation."""

    busy_changed = Signal(bool)
    progress_changed = Signal(int, str)
    snapshot_changed = Signal(object)
    status_message = Signal(str)
    operation_succeeded = Signal(str)
    operation_failed = Signal(str)
    read_failed = Signal(str)
    task_status = Signal(str)
    database_changed = Signal(str, str)
    schedule_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def refresh(self) -> None:
        self.calls.append("refresh")

    def start_manual_backup(self) -> bool:
        self.calls.append("backup")
        return True

    def start_restore(self, _record: BackupRecord) -> bool:
        self.calls.append("restore")
        return True

    def start_relocation(self, _root: Path) -> bool:
        self.calls.append("relocate")
        return True

    def start_schedule_update(self, **_values: object) -> bool:
        self.calls.append("schedule")
        return True

    def validate_relocation(self, _root: Path) -> object | None:
        return None

    def load_task_status(self) -> None:
        self.calls.append("task_status")


class UnavailableFactory:
    """A factory that models a missing or invalid business data root."""

    def build_optional(self) -> object | None:
        return None

    def build(self, _config: AppConfig | None = None) -> object:
        raise AppError("read failed", user_message="History could not be read.")


class FakeScheduler:
    supported = True


class FakeTaskQuery:
    exists = True


class FakeScheduleService:
    scheduler = FakeScheduler()

    def task_status(self) -> FakeTaskQuery:
        return FakeTaskQuery()


class FakeWorkspace:
    schedule_service = FakeScheduleService()


class AvailableFactory:
    def build_optional(self) -> object:
        return FakeWorkspace()


class RefreshProbe(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.refresh_calls = 0

    def refresh(self) -> None:
        self.refresh_calls += 1


@pytest.fixture
def window_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def window(qapp, config_service: ConfigService, window_settings: QSettings) -> MainWindow:
    config = AppConfig(theme="light")
    config_service.save(config)
    viewmodel = ShellViewModel(config_service, config)
    main_window = MainWindow(viewmodel, ThemeManager(qapp), settings=window_settings)
    main_window.show()
    qapp.processEvents()
    yield main_window
    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


@pytest.fixture
def backup_view(qapp) -> BackupView:
    view = BackupView(FakeBackupViewModel())
    view.show()
    qapp.processEvents()
    yield view
    view.close()
    view.deleteLater()
    qapp.processEvents()


def _settings() -> BackupSettings:
    return BackupSettings(
        enabled=True,
        time="22:00",
        retention_days=30,
        keep_minimum=5,
    )


def _record(status: BackupStatus, name: str) -> BackupRecord:
    return BackupRecord(
        path=Path("Backups") / name,
        backup_type=BackupType.MANUAL,
        status=status,
        file_name=name,
        created_at_utc=datetime(2026, 11, 17, 10, 30, tzinfo=UTC),
        size_bytes=2048,
        schema_revision="0001_baseline",
    )


def _snapshot(tmp_path: Path, *records: BackupRecord) -> BackupSnapshot:
    root = tmp_path / "Business"
    return BackupSnapshot(
        available=True,
        unavailable_reason="",
        data_root=root,
        database_path=root / "Database" / "BusinessManagement.db",
        records=records,
        state=BackupState(),
        settings=_settings(),
    )


def _button(dialog: QDialog, text: str) -> QPushButton:
    matches = [button for button in dialog.findChildren(QPushButton) if button.text() == text]
    assert len(matches) == 1, [button.text() for button in dialog.findChildren(QPushButton)]
    return matches[0]


def test_generated_stylesheets_are_complete_and_tokenized() -> None:
    light = build_stylesheet(LIGHT_PALETTE)
    dark = build_stylesheet(DARK_PALETTE)

    for sheet, palette in ((light, LIGHT_PALETTE), (dark, DARK_PALETTE)):
        assert palette.bg_app in sheet
        assert palette.primary in sheet
        assert "$" not in sheet
        assert "pxpx" not in sheet
        assert not re.search(
            r"(?m)^\s*(?:padding|width|height|min-height|min-width|spacing):\s*[1-9]\d*\s*;",
            sheet,
        )
        assert 'QPushButton[danger="true"]' in sheet
        assert 'QLabel[checkStatus="warning"]' in sheet
        assert "QTreeWidget::item:selected" in sheet
        assert "QScrollBar::handle:vertical" in sheet

    assert light != dark
    assert LIGHT_CHART_PALETTE.series[0] == LIGHT_PALETTE.primary
    assert DARK_CHART_PALETTE.series[0] == DARK_PALETTE.primary
    assert LIGHT_CHART_PALETTE != DARK_CHART_PALETTE


def test_theme_manager_syncs_qt_palette(qapp) -> None:
    manager = ThemeManager(qapp)
    try:
        manager.apply("dark")
        dark_color = qapp.palette().color(QPalette.ColorRole.Highlight).name().upper()
        assert dark_color == DARK_PALETTE.primary
        manager.apply("light")
        light_color = qapp.palette().color(QPalette.ColorRole.Highlight).name().upper()
        assert light_color == LIGHT_PALETTE.primary
    finally:
        manager.apply("light")


def test_status_badge_exposes_tone_without_color_only(qapp) -> None:
    badge = StatusBadge("Reading", None)
    try:
        assert badge.tone == "info"
        badge.set_status("Verified", "pass")
        assert badge.tone == "pass"
        assert badge.property("checkStatus") == "pass"
        assert badge.accessibleName() == "Success: Verified"
        with pytest.raises(ValueError):
            apply_status(badge, "unknown")
    finally:
        badge.close()


def test_empty_state_and_detail_card_are_reusable(qapp) -> None:
    empty = EmptyState("Nothing yet", "Details explain why.")
    card = DetailCard("Facts")
    try:
        assert empty.accessibleName() == "Nothing yet"
        assert empty.title_label.text() == "Nothing yet"
        assert empty.detail_label.text() == "Details explain why."
        assert empty.detail_label.isVisible() is False

        value = card.add_row("Folder", "C:/Business")
        assert value.text() == "C:/Business"
        assert value.accessibleName() == "Folder: C:/Business"
    finally:
        empty.close()
        card.close()


def test_button_helper_and_dialog_sizing(qapp) -> None:
    dialog = QDialog()
    try:
        secondary = make_button(
            "Cancel", dialog, variant="secondary", accessible_name="Cancel safely"
        )
        save = make_button("Save", dialog, default=True)
        assert secondary.property("secondary") is True
        assert secondary.accessibleName() == "Cancel safely"
        assert save.isDefault() is True
        with pytest.raises(ValueError):
            make_button("Bad", dialog, variant="ghost")

        set_dialog_size(dialog, 1200, 900, minimum_width=620, minimum_height=420)
        assert dialog.width() <= 1200
        assert dialog.height() <= 900
        assert dialog.minimumWidth() <= dialog.width()
        assert dialog.minimumHeight() <= dialog.height()
    finally:
        dialog.close()


def test_toast_is_non_modal_and_accessible(qapp) -> None:
    parent = QWidget()
    parent.resize(640, 480)
    parent.show()
    qapp.processEvents()
    try:
        toast = show_toast(parent, "Backup created", tone="pass")
        qapp.processEvents()
        assert isinstance(toast, Toast)
        assert toast.isVisible() is True
        assert toast.parent() is parent
        assert toast.accessibleName() == "Success: Backup created"
        assert toast.property("tone") == "pass"
    finally:
        parent.close()


def test_window_persists_navigation_and_geometry(
    qapp, config_service: ConfigService, window_settings: QSettings, tmp_path: Path
) -> None:
    def build() -> MainWindow:
        config = AppConfig(theme="light")
        config_service.save(config)
        viewmodel = ShellViewModel(config_service, config)
        result = MainWindow(viewmodel, ThemeManager(qapp), settings=window_settings)
        result.show()
        return result

    first = build()
    try:
        first.navigate("sales")
        first.resize(1280, 720)
        first.close()
        window_settings.sync()
        assert first.current_key == "sales"
        assert window_settings.value("window/geometry") is not None
    finally:
        first.deleteLater()
        qapp.processEvents()

    second = build()
    try:
        assert second.current_key == "sales"
        assert second.sidebar.button("sales").isChecked() is True
        assert second.width() >= 1280
        assert second.height() >= 720
    finally:
        second.close()
        second.deleteLater()
        qapp.processEvents()


def test_window_exposes_accessible_shell_controls(window: MainWindow) -> None:
    assert window.statusBar().accessibleName() == "Application status"
    assert window.sidebar.button("backup").accessibleName() == "Backup"
    assert window.top_bar.theme_button.accessibleName() == "Switch to dark theme"
    labels = {label.accessibleName() for label in window.findChildren(QLabel)}
    assert "Database status" in labels
    assert "Default currency" in labels
    assert "Local-only operation" in labels


def test_f5_refresh_shortcut_calls_current_view(window: MainWindow, qapp) -> None:
    shortcut = window.findChild(QShortcut)
    assert shortcut is not None
    assert shortcut.context() == Qt.ShortcutContext.WindowShortcut

    probe = RefreshProbe(window)
    window.content_stack.addWidget(probe)
    window.content_stack.setCurrentWidget(probe)
    QTest.keyClick(window, Qt.Key.Key_F5)
    qapp.processEvents()

    assert probe.refresh_calls == 1


def test_backup_view_renders_history_and_guards_restore(
    backup_view: BackupView, tmp_path: Path
) -> None:
    records = (
        _record(BackupStatus.VERIFIED, "verified.db"),
        _record(BackupStatus.MISSING, "gone.db"),
    )
    backup_view.viewmodel.snapshot_changed.emit(_snapshot(tmp_path, *records))

    assert backup_view.history_tree.topLevelItemCount() == 2
    assert backup_view.restore_button.isEnabled() is False
    assert backup_view.move_button.isEnabled() is True
    assert backup_view.empty_state.isVisible() is False

    backup_view.history_tree.setCurrentItem(backup_view.history_tree.topLevelItem(0))
    assert backup_view.restore_button.isEnabled() is True
    assert backup_view.viewmodel.calls == ["refresh"]

    backup_view.history_tree.setCurrentItem(backup_view.history_tree.topLevelItem(1))
    assert backup_view.restore_button.isEnabled() is False

    backup_view.backup_button.click()
    assert backup_view.viewmodel.calls[-1] == "backup"


def test_backup_view_shows_empty_unavailable_and_busy_states(
    backup_view: BackupView, tmp_path: Path
) -> None:
    backup_view.viewmodel.snapshot_changed.emit(_snapshot(tmp_path))
    assert backup_view.history_tree.isVisible() is False
    assert backup_view.empty_state.isVisible() is True

    unavailable = BackupSnapshot(
        available=False,
        unavailable_reason="The configured data drive is not available.",
        data_root=tmp_path / "Business",
        database_path=None,
        records=(),
        state=BackupState(),
        settings=_settings(),
    )
    backup_view.viewmodel.snapshot_changed.emit(unavailable)
    assert backup_view.status_label.tone == "warning"
    assert backup_view.location_text("last_backup") == "Unavailable"
    assert backup_view.backup_button.isEnabled() is False

    verified = _record(BackupStatus.VERIFIED, "v.db")
    backup_view.viewmodel.snapshot_changed.emit(_snapshot(tmp_path, verified))
    backup_view.viewmodel.busy_changed.emit(True)
    assert backup_view.progress_bar.isVisible() is True
    assert backup_view.backup_button.isEnabled() is False
    assert backup_view.refresh_button.isEnabled() is False
    backup_view.viewmodel.busy_changed.emit(False)
    assert backup_view.backup_button.isEnabled() is True


def test_backup_view_feedback_uses_status_and_modal_error(
    backup_view: BackupView, monkeypatch: pytest.MonkeyPatch
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        staticmethod(lambda _parent, _title, message, *_args: messages.append(message)),
    )

    backup_view.viewmodel.operation_succeeded.emit("Backup created")
    assert backup_view.status_label.tone == "pass"
    assert backup_view.findChildren(Toast)

    backup_view.viewmodel.read_failed.emit("History could not be read")
    assert backup_view.status_label.tone == "warning"
    assert messages == []

    backup_view.viewmodel.operation_failed.emit("Restore failed")
    assert backup_view.status_label.tone == "error"
    assert messages == ["Restore failed"]


def test_backup_viewmodel_reports_read_failures_without_modal_signal(
    config_service: ConfigService,
) -> None:
    viewmodel = BackupViewModel(
        UnavailableFactory(),
        config_service,
        None,
        runner=InlineTaskRunner(),
    )
    read_failures: list[str] = []
    failures: list[str] = []
    statuses: list[str] = []
    viewmodel.read_failed.connect(read_failures.append)
    viewmodel.operation_failed.connect(failures.append)
    viewmodel.task_status.connect(statuses.append)

    viewmodel.refresh()
    viewmodel.load_task_status()

    assert read_failures == ["History could not be read."]
    assert failures == []
    assert statuses == ["Automatic backups are unavailable."]
    assert viewmodel.is_busy is False


def test_backup_viewmodel_task_status_uses_async_signal(config_service: ConfigService) -> None:
    viewmodel = BackupViewModel(
        AvailableFactory(),
        config_service,
        None,
        runner=InlineTaskRunner(),
    )
    statuses: list[str] = []
    viewmodel.task_status.connect(statuses.append)

    viewmodel.load_task_status()

    assert statuses == ["The Windows backup task is registered."]


def test_backup_settings_dialog_defaults_and_async_status(qapp) -> None:
    dialog = BackupSettingsDialog(_settings(), task_status="Checking...")
    try:
        save = _button(dialog, "Save schedule")
        cancel = _button(dialog, "Cancel")
        assert save.isDefault() is True
        assert save.shortcut() == QKeySequence.StandardKey.Save
        assert cancel.accessibleName() == "Cancel"
        assert "Checking..." in [label.text() for label in dialog.findChildren(QLabel)]

        dialog.set_task_status("The Windows backup task is registered.")
        status = next(
            label
            for label in dialog.findChildren(QLabel)
            if label.accessibleName().startswith("Windows task status:")
        )
        assert status.text() == "The Windows backup task is registered."
        assert status.accessibleName() == (
            "Windows task status: The Windows backup task is registered."
        )
    finally:
        dialog.close()


def test_restore_dialog_keeps_cancel_as_safe_default(qapp) -> None:
    record = _record(BackupStatus.VERIFIED, "verified.db")
    dialog = RestoreConfirmationDialog(record, current_database=Path("C:/Business/live.db"))
    try:
        cancel = _button(dialog, "Cancel")
        restore = _button(dialog, "Restore this backup")
        assert cancel.isDefault() is True
        assert restore.isDefault() is False
        assert restore.accessibleName() == "Replace the current database with verified.db"
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        assert "verified.db" in texts
        assert "0001_baseline" in texts
        assert any("safety backup" in text for text in texts)
    finally:
        dialog.close()


def test_recovery_dialog_default_focus_and_safe_exit(qapp) -> None:
    dialog = RecoveryDialog("The configured drive is not available.")
    dialog.show()
    qapp.processEvents()
    try:
        retry = _button(dialog, "Retry")
        exit_button = _button(dialog, "Exit")
        assert retry.isDefault() is True
        assert QApplication.focusWidget() is retry
        assert exit_button.isDefault() is False
        assert exit_button.accessibleName() == "Exit without changing any business data"
        assert dialog.action is RecoveryAction.EXIT
    finally:
        dialog.close()


def _write_smoke_config(tmp_path: Path, root: Path, database_path: Path) -> None:
    config_dir = tmp_path / "Roaming" / "GobindasBMS"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "data_root": str(root),
        "database_path": str(database_path),
    }
    (config_dir / "config.json").write_text(json.dumps(payload), encoding="utf-8")


def _create_smoke_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(DatabaseConfig(path=path))
    try:
        MigrationManager(database).create_database()
    finally:
        database.shutdown()


@pytest.mark.parametrize("scale", ["1", "1.25", "1.5"])
def test_programmatic_smoke_at_scale_factors(tmp_path: Path, scale: str) -> None:
    root = tmp_path / "business"
    database_path = root / "Database" / "BusinessManagement.db"
    _create_smoke_database(database_path)
    _write_smoke_config(tmp_path, root, database_path)

    environment = os.environ.copy()
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_SCALE_FACTOR=scale,
        APPDATA=str(tmp_path / "Roaming"),
        LOCALAPPDATA=str(tmp_path / "Local"),
        PYTHONPATH=str(PROJECT_ROOT),
        GOBINDAS_MUTEX_NAME=rf"Local\GGBMS.Phase05.{uuid.uuid4().hex}",
    )
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--smoke-test"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    log = (tmp_path / "Local" / "GobindasBMS" / "logs" / "app.log").read_text(
        encoding="utf-8"
    )
    assert "Main window shown" in log
    assert "CRITICAL" not in log
    assert "Traceback" not in log
