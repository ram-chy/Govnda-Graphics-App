"""Blocking recovery dialog for configuration and missing-drive problems.

The dialog never creates, moves, or changes a database. It only records the
user's choice and returns it to the startup coordinator.
"""

from __future__ import annotations

from enum import StrEnum
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

from app.core import constants
from app.ui.themes.tokens import METRICS


class RecoveryAction(StrEnum):
    """What the user chose on the recovery dialog."""

    RETRY = "retry"
    LOCATE = "locate"
    NEW_SETUP = "new_setup"
    EXIT = "exit"


class RecoveryDialog(QDialog):
    """Explain why startup stopped and offer only safe recovery choices."""

    def __init__(
        self,
        message: str,
        *,
        database_path: Path | None = None,
        data_root: Path | None = None,
        quarantine_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RecoveryDialog")
        self.setWindowTitle(f"{constants.APP_SHORT_NAME} - business data needs attention")
        self.setModal(True)
        self.resize(720, 480)
        self.setMinimumSize(620, 420)
        self._action = RecoveryAction.EXIT
        self._build_ui(message, database_path, data_root, quarantine_path)

    @property
    def action(self) -> RecoveryAction:
        return self._action

    def _build_ui(
        self,
        message: str,
        database_path: Path | None,
        data_root: Path | None,
        quarantine_path: Path | None,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("The business database cannot be opened", self)
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        explanation = QLabel(message, self)
        explanation.setObjectName("WizardBody")
        explanation.setWordWrap(True)
        explanation.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(explanation)

        card = QFrame(self)
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            METRICS.space_5, METRICS.space_4, METRICS.space_5, METRICS.space_4
        )
        card_layout.setSpacing(METRICS.space_2)
        card_title = QLabel("Saved and preserved locations", card)
        card_title.setObjectName("SectionTitle")
        card_layout.addWidget(card_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(METRICS.space_4)
        grid.setVerticalSpacing(METRICS.space_2)
        columns = (
            ("Database file", str(database_path) if database_path else "(not configured)"),
            ("Data root", str(data_root) if data_root else "(not configured)"),
            (
                "Preserved configuration",
                str(quarantine_path) if quarantine_path else "(not moved)",
            ),
        )
        for row, (caption, value) in enumerate(columns):
            caption_label = QLabel(caption, card)
            caption_label.setObjectName("FieldLabel")
            value_label = QLabel(value, card)
            value_label.setObjectName("WizardPath")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            grid.addWidget(caption_label, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(value_label, row, 1)
        grid.setColumnStretch(1, 1)
        card_layout.addLayout(grid)
        layout.addWidget(card)

        safety = QLabel(
            "No replacement database was created and no saved path was changed. "
            "If the drive is disconnected, reconnect it and choose Retry.",
            self,
        )
        safety.setObjectName("MetaLabel")
        safety.setWordWrap(True)
        layout.addWidget(safety)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(METRICS.space_2)
        locate = QPushButton("Locate existing data...", self)
        locate.setProperty("secondary", True)
        locate.clicked.connect(lambda: self._choose(RecoveryAction.LOCATE))
        buttons.addWidget(locate)

        new_setup = QPushButton("Start a new setup...", self)
        new_setup.setProperty("secondary", True)
        new_setup.clicked.connect(lambda: self._choose(RecoveryAction.NEW_SETUP))
        buttons.addWidget(new_setup)

        buttons.addStretch(1)

        exit_button = QPushButton("Exit", self)
        exit_button.setProperty("danger", True)
        exit_button.clicked.connect(lambda: self._choose(RecoveryAction.EXIT, close=True))
        buttons.addWidget(exit_button)

        retry = QPushButton("Retry", self)
        retry.setDefault(True)
        retry.clicked.connect(lambda: self._choose(RecoveryAction.RETRY))
        buttons.addWidget(retry)
        layout.addLayout(buttons)

    def _choose(self, action: RecoveryAction, *, close: bool = False) -> None:
        self._action = action
        if close:
            self.reject()
        else:
            self.accept()


__all__ = ["RecoveryAction", "RecoveryDialog"]
