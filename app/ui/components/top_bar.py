"""Top context bar: page title, subtitle, and theme toggle."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from app.ui.themes.tokens import METRICS


class TopBar(QFrame):
    """Flat header above the content area."""

    theme_toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(METRICS.topbar_height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.space_2,
            METRICS.content_margin_horizontal,
            METRICS.space_2,
        )
        layout.setSpacing(METRICS.space_4)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(0)

        self.title_label = QLabel("Dashboard", self)
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel("", self)
        self.subtitle_label.setObjectName("PageSubtitle")
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        layout.addLayout(titles)
        layout.addStretch(1)

        self.theme_button = QToolButton(self)
        self.theme_button.setObjectName("ThemeButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.theme_button.clicked.connect(self.theme_toggle_requested)
        layout.addWidget(self.theme_button)

        self.set_theme(is_dark=False)

    def set_page(self, title: str, subtitle: str = "") -> None:
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def set_theme(self, *, is_dark: bool) -> None:
        """Label the button with the action it performs, not the current state."""
        if is_dark:
            self.theme_button.setText("Light mode")
            self.theme_button.setToolTip("Switch to the light theme")
            self.theme_button.setAccessibleName("Switch to light theme")
        else:
            self.theme_button.setText("Dark mode")
            self.theme_button.setToolTip("Switch to the dark theme")
            self.theme_button.setAccessibleName("Switch to dark theme")
