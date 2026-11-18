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
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.ui.components.controls import DetailCard, make_button, set_dialog_size
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
        set_dialog_size(
            self,
            METRICS.dialog_width,
            METRICS.dialog_height + METRICS.space_3,
            minimum_width=METRICS.dialog_minimum_width,
            minimum_height=METRICS.dialog_minimum_height,
        )
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

        card = DetailCard("Saved and preserved locations", self)
        columns = (
            ("Database file", str(database_path) if database_path else "(not configured)"),
            ("Data root", str(data_root) if data_root else "(not configured)"),
            (
                "Preserved configuration",
                str(quarantine_path) if quarantine_path else "(not moved)",
            ),
        )
        for caption, value in columns:
            card.add_row(caption, value, self)
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
        locate = make_button("Locate existing data...", self, variant="secondary")
        locate.clicked.connect(lambda: self._choose(RecoveryAction.LOCATE))
        buttons.addWidget(locate)

        new_setup = make_button("Start a new setup...", self, variant="secondary")
        new_setup.clicked.connect(lambda: self._choose(RecoveryAction.NEW_SETUP))
        buttons.addWidget(new_setup)

        buttons.addStretch(1)

        exit_button = make_button(
            "Exit",
            self,
            variant="danger",
            accessible_name="Exit without changing any business data",
        )
        exit_button.clicked.connect(lambda: self._choose(RecoveryAction.EXIT, close=True))
        buttons.addWidget(exit_button)

        retry = make_button("Retry", self, default=True)
        retry.setToolTip("Check the saved data location again")
        retry.clicked.connect(lambda: self._choose(RecoveryAction.RETRY))
        buttons.addWidget(retry)

        # Safe retry first in the tab order; Exit is deliberately separated from
        # the two setup choices and is never the default action.
        self.setTabOrder(retry, locate)
        self.setTabOrder(locate, new_setup)
        self.setTabOrder(new_setup, exit_button)
        retry.setFocus()
        layout.addLayout(buttons)

    def _choose(self, action: RecoveryAction, *, close: bool = False) -> None:
        self._action = action
        if close:
            self.reject()
        else:
            self.accept()


__all__ = ["RecoveryAction", "RecoveryDialog"]
