"""Backup schedule and retention settings dialog.

The dialog only collects values. Validation, Windows Task Scheduler registration,
and atomic configuration writes happen in :class:`ScheduleService`.
"""

from __future__ import annotations

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.services.schedule_service import BackupSettings
from app.ui.themes.tokens import METRICS


class BackupSettingsDialog(QDialog):
    """Collect the daily schedule and retention policy."""

    def __init__(
        self,
        settings: BackupSettings,
        *,
        task_status: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BackupSettingsDialog")
        self.setWindowTitle("Backup schedule and retention")
        self.setModal(True)
        self.resize(620, 460)
        self.setMinimumSize(560, 420)
        self._build_ui(settings, task_status)

    @property
    def enabled(self) -> bool:
        return self._enabled.isChecked()

    @property
    def time_text(self) -> str:
        return self._time.time().toString("HH:mm")

    @property
    def retention_days(self) -> int:
        return int(self._retention.value())

    @property
    def keep_minimum(self) -> int:
        return int(self._keep.value())

    def _build_ui(self, settings: BackupSettings, task_status: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("Automatic backup schedule", self)
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        body = QLabel(
            "A verified automatic backup is created once per day. Manual and safety "
            "backups are never removed by the automatic retention policy.",
            self,
        )
        body.setObjectName("WizardBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        self._enabled = QCheckBox("Create a daily automatic backup", self)
        self._enabled.setChecked(settings.enabled)
        layout.addWidget(self._enabled)

        form = QFormLayout()
        form.setHorizontalSpacing(METRICS.space_4)
        form.setVerticalSpacing(METRICS.space_3)

        self._time = QTimeEdit(self)
        self._time.setDisplayFormat("HH:mm")
        hour, minute = _parse_time(settings.time)
        self._time.setTime(QTime(hour, minute))
        form.addRow("Backup time (local Windows time)", self._time)

        self._retention = QSpinBox(self)
        self._retention.setRange(
            constants.BACKUP_RETENTION_MINIMUM_DAYS,
            constants.BACKUP_RETENTION_MAXIMUM_DAYS,
        )
        self._retention.setValue(settings.retention_days)
        self._retention.setSuffix(" days")
        form.addRow("Keep automatic backups for", self._retention)

        self._keep = QSpinBox(self)
        self._keep.setRange(
            constants.BACKUP_KEEP_MINIMUM_FLOOR,
            constants.BACKUP_KEEP_MINIMUM_CEILING,
        )
        self._keep.setValue(settings.keep_minimum)
        self._keep.setSuffix(" backups")
        form.addRow("Always keep at least", self._keep)
        layout.addLayout(form)

        status = QLabel(task_status, self)
        status.setObjectName("MetaLabel")
        status.setWordWrap(True)
        layout.addWidget(status)

        limitation = QLabel(
            "The scheduled task runs under this Windows user account and only while that "
            "user is logged on. Automatic catch-up runs the next time the application "
            "starts if a scheduled backup was missed.",
            self,
        )
        limitation.setObjectName("MetaLabel")
        limitation.setWordWrap(True)
        layout.addWidget(limitation)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(METRICS.space_2)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel", self)
        cancel.setProperty("secondary", True)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Save schedule", self)
        save.setDefault(True)
        save.clicked.connect(self.accept)
        buttons.addWidget(save)
        layout.addLayout(buttons)


def _parse_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":")
        return int(hour_text), int(minute_text)
    except (AttributeError, TypeError, ValueError):
        hour_text, minute_text = constants.DEFAULT_BACKUP_TIME.split(":")
        return int(hour_text), int(minute_text)


__all__ = ["BackupSettingsDialog"]
