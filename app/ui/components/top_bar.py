"""Top context bar: page title, subtitle, and theme toggle."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from app.ui.themes.tokens import METRICS


class TopBar(QFrame):
    """Flat header above the content area."""

    theme_toggle_requested = Signal()
    user_management_requested = Signal()
    change_password_requested = Signal()
    logout_requested = Signal()

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

        self.user_button = QToolButton(self)
        self.user_button.setObjectName("AccountUsersButton")
        self.user_button.setText("Users")
        self.user_button.setToolTip("Manage local user accounts")
        self.user_button.setAccessibleName("Manage local user accounts")
        self.user_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.user_button.clicked.connect(self.user_management_requested)
        self.user_button.setVisible(False)
        layout.addWidget(self.user_button)

        self.password_button = QToolButton(self)
        self.password_button.setObjectName("AccountPasswordButton")
        self.password_button.setText("Password")
        self.password_button.setToolTip("Change your password")
        self.password_button.setAccessibleName("Change your password")
        self.password_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.password_button.clicked.connect(self.change_password_requested)
        self.password_button.setVisible(False)
        layout.addWidget(self.password_button)

        self.logout_button = QToolButton(self)
        self.logout_button.setObjectName("AccountLogoutButton")
        self.logout_button.setText("Log out")
        self.logout_button.setToolTip("End this session")
        self.logout_button.setAccessibleName("Log out")
        self.logout_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.logout_button.clicked.connect(self.logout_requested)
        self.logout_button.setVisible(False)
        layout.addWidget(self.logout_button)

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
