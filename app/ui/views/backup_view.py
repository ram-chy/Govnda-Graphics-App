"""Backup, restore, relocation, and schedule screen.

The view is presentation only. Every safety decision (verification, locking,
retention, restore ordering) is made by the application services through
:class:`~app.ui.viewmodels.backup_viewmodel.BackupViewModel`. Long operations
run on a background worker, so this widget only renders results and progress.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.domain.backup import BackupRecord, BackupStatus
from app.ui.components.cards import SectionCard
from app.ui.dialogs.backup_settings_dialog import BackupSettingsDialog
from app.ui.dialogs.restore_confirmation_dialog import RestoreConfirmationDialog
from app.ui.formatting import format_backup_size, format_backup_time, format_status
from app.ui.themes.tokens import METRICS
from app.ui.viewmodels.backup_viewmodel import BackupSnapshot, BackupViewModel

logger = logging.getLogger(__name__)

_HISTORY_COLUMNS = ("Type", "File", "Status", "Created", "Size", "Schema")


class BackupView(QWidget):
    """Backup status, history, progress, and the safety-sensitive actions."""

    def __init__(self, viewmodel: BackupViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentArea")
        self._viewmodel = viewmodel
        self._snapshot: BackupSnapshot | None = None
        self._records: tuple[BackupRecord, ...] = ()

        self._build_ui()
        self._connect_signals()
        self._set_busy(False)
        self._viewmodel.refresh()

    @property
    def viewmodel(self) -> BackupViewModel:
        return self._viewmodel

    @property
    def history_tree(self) -> QTreeWidget:
        return self._history

    @property
    def progress_bar(self) -> QProgressBar:
        return self._progress

    @property
    def status_label(self) -> QLabel:
        return self._status

    @property
    def backup_button(self) -> QPushButton:
        return self._backup_button

    @property
    def restore_button(self) -> QPushButton:
        return self._restore_button

    @property
    def move_button(self) -> QPushButton:
        return self._move_button

    @property
    def schedule_button(self) -> QPushButton:
        return self._schedule_button

    @property
    def refresh_button(self) -> QPushButton:
        return self._refresh_button

    def location_text(self, key: str) -> str:
        return self._locations[key].text()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_4)

        header = QHBoxLayout()
        header.setSpacing(METRICS.space_2)
        title = QLabel("Backup and data safety", self)
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)

        self._refresh_button = QPushButton("Refresh", self)
        self._refresh_button.setProperty("secondary", True)
        self._refresh_button.clicked.connect(self._viewmodel.refresh)
        header.addWidget(self._refresh_button)

        self._backup_button = QPushButton("Back up now", self)
        self._backup_button.clicked.connect(self._on_backup_now)
        header.addWidget(self._backup_button)
        layout.addLayout(header)

        self._status = QLabel("", self)
        self._status.setObjectName("MetaLabel")
        self._status.setWordWrap(True)
        self._status.setProperty("checkStatus", "info")
        layout.addWidget(self._status)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        locations = SectionCard("Locations and last result", self)
        grid = QGridLayout()
        grid.setHorizontalSpacing(METRICS.space_4)
        grid.setVerticalSpacing(METRICS.space_2)
        self._locations: dict[str, QLabel] = {}
        rows = (
            ("data_root", "Business data folder"),
            ("database", "Live database"),
            ("backups", "Backup storage"),
            ("last_backup", "Last successful backup"),
            ("last_attempt", "Last attempt"),
            ("last_failure", "Last failure"),
        )
        for row, (key, caption) in enumerate(rows):
            caption_label = QLabel(caption, self)
            caption_label.setObjectName("FieldLabel")
            value_label = QLabel("Not read yet", self)
            value_label.setObjectName("WizardPath")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            grid.addWidget(caption_label, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(value_label, row, 1)
            self._locations[key] = value_label
        grid.setColumnStretch(1, 1)
        locations.content_layout.addLayout(grid)
        layout.addWidget(locations)

        schedule = SectionCard("Automatic backup schedule", self)
        self._schedule_summary = QLabel("Not read yet", self)
        self._schedule_summary.setWordWrap(True)
        schedule.add_widget(self._schedule_summary)
        schedule_actions = QHBoxLayout()
        schedule_actions.addStretch(1)
        self._schedule_button = QPushButton("Schedule settings", self)
        self._schedule_button.setProperty("secondary", True)
        self._schedule_button.clicked.connect(self._on_schedule_settings)
        schedule_actions.addWidget(self._schedule_button)
        schedule.content_layout.addLayout(schedule_actions)
        layout.addWidget(schedule)

        history = SectionCard("Backup history", self)
        history_note = QLabel(
            "Every entry below is rebuilt from the managed backup folders. Only a "
            "verified backup can be restored.",
            self,
        )
        history_note.setObjectName("MetaLabel")
        history_note.setWordWrap(True)
        history.add_widget(history_note)

        self._history = QTreeWidget(self)
        self._history.setColumnCount(len(_HISTORY_COLUMNS))
        self._history.setHeaderLabels(list(_HISTORY_COLUMNS))
        self._history.setRootIsDecorated(False)
        self._history.setAlternatingRowColors(True)
        self._history.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._history.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._history.setMinimumHeight(220)
        header_view = self._history.header()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._history.itemSelectionChanged.connect(self._update_action_state)
        history.add_widget(self._history)

        history_actions = QHBoxLayout()
        history_actions.setSpacing(METRICS.space_2)
        self._restore_button = QPushButton("Restore selected backup", self)
        self._restore_button.setProperty("danger", True)
        self._restore_button.clicked.connect(self._on_restore_selected)
        history_actions.addWidget(self._restore_button)
        history_actions.addStretch(1)
        self._move_button = QPushButton("Move database...", self)
        self._move_button.setProperty("secondary", True)
        self._move_button.clicked.connect(self._on_move_database)
        history_actions.addWidget(self._move_button)
        history.content_layout.addLayout(history_actions)
        layout.addWidget(history, 1)

    def _connect_signals(self) -> None:
        self._viewmodel.busy_changed.connect(self._set_busy)
        self._viewmodel.progress_changed.connect(self._on_progress)
        self._viewmodel.snapshot_changed.connect(self._render_snapshot)
        self._viewmodel.status_message.connect(self._show_status)
        self._viewmodel.operation_succeeded.connect(self._on_success)
        self._viewmodel.operation_failed.connect(self._on_failure)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._progress.setVisible(busy)
        if not busy:
            self._progress.setValue(0)
        else:
            self._progress.setValue(0)
        self._refresh_button.setEnabled(not busy)
        self._update_action_state()

    def _update_action_state(self) -> None:
        busy = self._busy
        available = bool(self._snapshot and self._snapshot.available)
        self._backup_button.setEnabled(available and not busy)
        self._schedule_button.setEnabled(available and not busy)
        self._move_button.setEnabled(available and not busy)
        self._restore_button.setEnabled(
            available and not busy and self._selected_verified_record() is not None
        )

    def _on_progress(self, percent: int, message: str) -> None:
        self._progress.setValue(max(0, min(100, percent)))
        if message:
            self._show_status(message)

    def _show_status(self, message: str) -> None:
        if not message:
            return
        self._status.setText(message)
        self._apply_status_property("info")

    def _on_success(self, message: str) -> None:
        self._status.setText(message)
        self._apply_status_property("pass")

    def _on_failure(self, message: str) -> None:
        self._status.setText(message)
        self._apply_status_property("error")
        QMessageBox.critical(self, "Backup operation did not complete", message)

    def _apply_status_property(self, value: str) -> None:
        self._status.setProperty("checkStatus", value)
        style = self._status.style()
        if style is not None:
            style.unpolish(self._status)
            style.polish(self._status)

    def _render_snapshot(self, snapshot: object) -> None:
        assert isinstance(snapshot, BackupSnapshot)
        self._snapshot = snapshot
        self._records = snapshot.records

        if not snapshot.available:
            self._locations["data_root"].setText(
                str(snapshot.data_root) if snapshot.data_root else "Not configured"
            )
            self._locations["database"].setText(
                str(snapshot.database_path) if snapshot.database_path else "Not configured"
            )
            self._locations["backups"].setText("Unavailable")
            self._locations["last_backup"].setText("Unavailable")
            self._locations["last_attempt"].setText("Unavailable")
            self._locations["last_failure"].setText("Unavailable")
            self._schedule_summary.setText(snapshot.unavailable_reason)
            self._history.clear()
            self._show_status(snapshot.unavailable_reason)
            self._apply_status_property("warning")
            self._update_action_state()
            return

        data_root = snapshot.data_root
        self._locations["data_root"].setText(str(data_root) if data_root else "Not configured")
        self._locations["database"].setText(
            str(snapshot.database_path) if snapshot.database_path else "Not configured"
        )
        backups_root = (
            data_root / constants.DATA_BACKUPS_DIR if data_root is not None else None
        )
        self._locations["backups"].setText(
            str(backups_root) if backups_root is not None else "Not configured"
        )

        state = snapshot.state
        if state.last_success_utc is not None:
            file_name = state.last_success_file or "Unknown file"
            type_text = state.last_success_type or "unknown"
            self._locations["last_backup"].setText(
                f"{format_backup_time(state.last_success_utc)} - {type_text} - {file_name}"
            )
        else:
            latest = snapshot.latest_verified()
            if latest is not None:
                self._locations["last_backup"].setText(
                    f"{format_backup_time(latest.created_at_utc)} - "
                    f"{latest.backup_type.label} - {latest.file_name}"
                )
            else:
                self._locations["last_backup"].setText("No verified backup yet")

        if state.last_attempt_utc is not None:
            result = state.last_attempt_result or "unknown"
            self._locations["last_attempt"].setText(
                f"{format_backup_time(state.last_attempt_utc)} - {result}"
            )
        else:
            self._locations["last_attempt"].setText("No attempt recorded")

        if state.last_failure_utc is not None:
            detail = state.last_failure_message or "No detail recorded"
            self._locations["last_failure"].setText(
                f"{format_backup_time(state.last_failure_utc)} - {detail}"
            )
        else:
            self._locations["last_failure"].setText("No failure recorded")

        settings = snapshot.settings
        if settings.enabled:
            enabled_text = f"Enabled daily at {settings.time} local time"
        else:
            enabled_text = "Disabled"
        self._schedule_summary.setText(
            f"{enabled_text}. Automatic backups are kept for {settings.retention_days} "
            f"days, with at least {settings.keep_minimum} retained. Manual and safety "
            "backups are never removed by retention."
        )

        self._populate_history(snapshot.records)
        self._update_action_state()

    def _populate_history(self, records: tuple[BackupRecord, ...]) -> None:
        selected = self._selected_record()
        selected_name = selected.file_name if selected is not None else None
        self._history.clear()
        for index, record in enumerate(records):
            item = QTreeWidgetItem(
                [
                    record.backup_type.label,
                    record.file_name,
                    format_status(record.status),
                    format_backup_time(record.created_at_utc, fallback="Unknown"),
                    format_backup_size(record.size_bytes),
                    record.schema_revision or "Unknown",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            if record.detail:
                item.setToolTip(1, record.detail)
            if record.status is not BackupStatus.VERIFIED:
                for column in range(len(_HISTORY_COLUMNS)):
                    item.setForeground(column, Qt.GlobalColor.gray)
            self._history.addTopLevelItem(item)
            if selected_name is not None and record.file_name == selected_name:
                self._history.setCurrentItem(item)

    def _selected_record(self) -> BackupRecord | None:
        item = self._history.currentItem()
        if item is None:
            return None
        index = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not 0 <= index < len(self._records):
            return None
        return self._records[index]

    def _selected_verified_record(self) -> BackupRecord | None:
        record = self._selected_record()
        if record is None or record.status is not BackupStatus.VERIFIED:
            return None
        return record

    def _on_backup_now(self) -> None:
        self._viewmodel.start_manual_backup()

    def _on_restore_selected(self) -> None:
        record = self._selected_verified_record()
        if record is None:
            self._show_status("Select a verified backup in the history first.")
            return
        current = self._snapshot.database_path if self._snapshot is not None else None
        dialog = RestoreConfirmationDialog(record, current_database=current, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._viewmodel.start_restore(record)

    def _on_schedule_settings(self) -> None:
        if self._snapshot is None:
            return
        dialog = BackupSettingsDialog(
            self._snapshot.settings,
            task_status=self._viewmodel.task_status_text(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._viewmodel.start_schedule_update(
            enabled=dialog.enabled,
            time=dialog.time_text,
            retention_days=dialog.retention_days,
            keep_minimum=dialog.keep_minimum,
        )

    def _on_move_database(self) -> None:
        if self._snapshot is None or self._snapshot.data_root is None:
            return
        start = str(self._snapshot.data_root.parent)
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choose a new business data folder",
            start,
        )
        if not chosen:
            return
        target = Path(chosen)
        validation = self._viewmodel.validate_relocation(target)
        if validation is None:
            return
        if not validation.is_valid:
            QMessageBox.critical(
                self,
                "The selected folder cannot be used",
                validation.error_summary,
            )
            return
        warning_text = ""
        if validation.warnings:
            warning_text = "\n\nWarnings:\n" + "\n".join(
                check.message for check in validation.warnings
            )
        confirmed = QMessageBox.question(
            self,
            "Move the business database?",
            f"The database will be copied to a verified location under:\n{target}\n\n"
            "A verified safety backup is created first. The old database file is kept and "
            "only the configuration is pointed at the new location."
            f"{warning_text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self._viewmodel.start_relocation(target)


__all__ = ["BackupView"]
