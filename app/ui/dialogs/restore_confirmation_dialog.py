"""Explicit restore confirmation.

Restore replaces the live database, so the user must see exactly which file will
be applied and which location will be changed. The destructive button is never
the default; Cancel is.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.domain.backup import BackupRecord
from app.ui.components.controls import DetailCard, make_button, set_dialog_size
from app.ui.formatting import format_backup_size, format_backup_time
from app.ui.themes.tokens import METRICS


class RestoreConfirmationDialog(QDialog):
    """Show the selected backup and require an explicit destructive choice."""

    def __init__(
        self,
        record: BackupRecord,
        *,
        current_database: Path | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._record = record
        self.setObjectName("RestoreConfirmationDialog")
        self.setWindowTitle("Restore a verified backup")
        self.setModal(True)
        set_dialog_size(
            self,
            METRICS.dialog_width,
            METRICS.dialog_height,
            minimum_width=METRICS.dialog_minimum_width,
            minimum_height=METRICS.dialog_minimum_height,
        )
        self._build_ui(current_database)

    @property
    def record(self) -> BackupRecord:
        return self._record

    def _build_ui(self, current_database: Path | None) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("Replace the current business database?", self)
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        warning = QLabel(
            "The current database contents will be replaced by the selected backup. "
            "A verified safety backup of the current database is created first, and the "
            "previous file is kept for rollback.",
            self,
        )
        warning.setObjectName("WizardBody")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        card = DetailCard("Selected backup", self)
        rows = (
            ("File", self._record.file_name),
            ("Created", format_backup_time(self._record.created_at_utc, fallback="Unknown")),
            ("Type", self._record.backup_type.label),
            ("Size", format_backup_size(self._record.size_bytes)),
            ("Schema revision", self._record.schema_revision or "Unknown"),
            ("Current database", str(current_database) if current_database else "Not configured"),
        )
        for caption, value in rows:
            card.add_row(caption, value, self)
        layout.addWidget(card)

        note = QLabel(
            "The selected file is verified again before it is staged. If anything fails "
            "after replacement, the previous database is restored and verified.",
            self,
        )
        note.setObjectName("MetaLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(METRICS.space_2)
        buttons.addStretch(1)
        cancel = make_button(
            "Cancel",
            self,
            variant="secondary",
            accessible_name="Cancel restore",
            default=True,
        )
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        restore = make_button(
            "Restore this backup",
            self,
            variant="danger",
            accessible_name=f"Replace the current database with {self._record.file_name}",
        )
        restore.clicked.connect(self.accept)
        buttons.addWidget(restore)
        self.setTabOrder(cancel, restore)
        layout.addLayout(buttons)


__all__ = ["RestoreConfirmationDialog"]
