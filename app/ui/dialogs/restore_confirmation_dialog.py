"""Explicit restore confirmation.

Restore replaces the live database, so the user must see exactly which file will
be applied and which location will be changed. The destructive button is never
the default; Cancel is.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.backup import BackupRecord
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
        self.resize(720, 460)
        self.setMinimumSize(620, 420)
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

        card = QFrame(self)
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            METRICS.space_5, METRICS.space_4, METRICS.space_5, METRICS.space_4
        )
        card_layout.setSpacing(METRICS.space_2)
        card_title = QLabel("Selected backup", card)
        card_title.setObjectName("SectionTitle")
        card_layout.addWidget(card_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(METRICS.space_4)
        grid.setVerticalSpacing(METRICS.space_2)
        rows = (
            ("File", self._record.file_name),
            ("Created", format_backup_time(self._record.created_at_utc, fallback="Unknown")),
            ("Type", self._record.backup_type.label),
            ("Size", format_backup_size(self._record.size_bytes)),
            ("Schema revision", self._record.schema_revision or "Unknown"),
            ("Current database", str(current_database) if current_database else "Not configured"),
        )
        for row, (caption, value) in enumerate(rows):
            caption_label = QLabel(caption, card)
            caption_label.setObjectName("FieldLabel")
            value_label = QLabel(value, card)
            value_label.setObjectName("WizardPath")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(caption_label, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(value_label, row, 1)
        grid.setColumnStretch(1, 1)
        card_layout.addLayout(grid)
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
        cancel = QPushButton("Cancel", self)
        cancel.setProperty("secondary", True)
        cancel.setDefault(True)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        restore = QPushButton("Restore this backup", self)
        restore.setProperty("danger", True)
        restore.clicked.connect(self.accept)
        buttons.addWidget(restore)
        layout.addLayout(buttons)


__all__ = ["RestoreConfirmationDialog"]
