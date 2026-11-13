"""Sidebar navigation with grouped, keyboard-accessible entries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.themes.tokens import METRICS


@dataclass(frozen=True, slots=True)
class NavItem:
    """One navigable destination in the shell."""

    key: str
    label: str
    subtitle: str = ""


@dataclass(frozen=True, slots=True)
class NavGroup:
    """A labelled group of navigation entries."""

    title: str
    items: tuple[NavItem, ...]


class Sidebar(QFrame):
    """Fixed-width navigation rail.

    The sidebar emits navigation intent only; it does not know about views or
    services. The main window owns navigation state.
    """

    navigation_requested = Signal(str)

    def __init__(self, groups: Sequence[NavGroup], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(METRICS.sidebar_width)

        self._buttons: dict[str, QToolButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(METRICS.space_2)

        brand_title = QLabel("Gobindas Graphics", self)
        brand_title.setObjectName("BrandTitle")
        brand_subtitle = QLabel("Business Management", self)
        brand_subtitle.setObjectName("BrandSubtitle")
        layout.addWidget(brand_title)
        layout.addWidget(brand_subtitle)

        divider = QFrame(self)
        divider.setObjectName("Divider")
        layout.addSpacing(METRICS.space_2)
        layout.addWidget(divider)
        layout.addSpacing(METRICS.space_1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        nav_container = QWidget(scroll)
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)

        for group in groups:
            group_label = QLabel(group.title, nav_container)
            group_label.setObjectName("NavGroupLabel")
            nav_layout.addWidget(group_label)
            for item in group.items:
                button = self._create_nav_button(item, nav_container)
                nav_layout.addWidget(button)
                self._buttons[item.key] = button
                self._button_group.addButton(button)

        nav_layout.addStretch(1)
        scroll.setWidget(nav_container)
        layout.addWidget(scroll, 1)

        footer = QLabel("Offline desktop application", self)
        footer.setObjectName("MetaLabel")
        layout.addWidget(footer)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._buttons)

    def button(self, key: str) -> QToolButton:
        try:
            return self._buttons[key]
        except KeyError as exc:
            raise KeyError(f"unknown navigation key: {key!r}") from exc

    def select(self, key: str, *, emit: bool = True) -> None:
        """Check the entry for ``key`` and optionally announce navigation."""
        button = self.button(key)
        with QSignalBlocker(button):
            button.setChecked(True)
        if emit:
            self.navigation_requested.emit(key)

    def set_active(self, key: str) -> None:
        """Update the checked entry without emitting navigation intent."""
        self.select(key, emit=False)

    def _create_nav_button(self, item: NavItem, parent: QWidget) -> QToolButton:
        button = QToolButton(parent)
        button.setText(item.label)
        button.setCheckable(True)
        button.setAutoRaise(False)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setMinimumHeight(METRICS.control_height)
        button.setProperty("nav", True)
        button.setAccessibleName(item.label)
        tooltip = item.subtitle or item.label
        button.setToolTip(tooltip)
        button.clicked.connect(lambda _checked=False, name=item.key: self._on_clicked(name))
        return button

    def _on_clicked(self, key: str) -> None:
        self.navigation_requested.emit(key)
