"""Small reusable controls built on the shared design tokens."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QPushButton, QWidget

from app.ui.components.cards import SectionCard
from app.ui.themes.tokens import METRICS

_VARIANTS = {"primary", "secondary", "danger"}


def set_dialog_size(
    dialog: QDialog,
    width: int,
    height: int,
    *,
    minimum_width: int,
    minimum_height: int,
) -> None:
    """Size a dialog from tokens while respecting 90% of the current screen."""
    screen = QApplication.primaryScreen()
    available = screen.availableGeometry() if screen is not None else None
    if available is not None:
        width = min(width, max(320, int(available.width() * 0.9)))
        height = min(height, max(320, int(available.height() * 0.9)))
    dialog.resize(width, height)
    dialog.setMinimumSize(min(minimum_width, width), min(minimum_height, height))


def make_button(
    text: str,
    parent: QWidget,
    *,
    variant: str = "primary",
    accessible_name: str | None = None,
    tooltip: str | None = None,
    default: bool = False,
) -> QPushButton:
    """Create a button with a consistent variant and accessible metadata."""
    if variant not in _VARIANTS:
        raise ValueError(f"unknown button variant: {variant!r}")
    button = QPushButton(text, parent)
    if variant != "primary":
        button.setProperty(variant, True)
    button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    button.setAccessibleName(accessible_name or text)
    if tooltip:
        button.setToolTip(tooltip)
    if default:
        button.setDefault(True)
    return button


class DetailCard(SectionCard):
    """A titled card that renders caption/value detail rows consistently."""

    def add_row(self, caption: str, value: str, parent: QWidget | None = None) -> QLabel:
        container = parent or self
        row = QGridLayout()
        row.setHorizontalSpacing(METRICS.space_4)
        row.setVerticalSpacing(METRICS.space_2)

        caption_label = QLabel(caption, container)
        caption_label.setObjectName("FieldLabel")
        value_label = QLabel(value, container)
        value_label.setObjectName("WizardPath")
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value_label.setAccessibleName(f"{caption}: {value}")

        row.addWidget(caption_label, 0, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(value_label, 0, 1)
        row.setColumnStretch(1, 1)
        self.content_layout.addLayout(row)
        return value_label


__all__ = ["DetailCard", "make_button", "set_dialog_size"]
