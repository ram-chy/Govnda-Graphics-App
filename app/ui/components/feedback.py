"""Lightweight, native Qt feedback components.

These widgets standardise status, empty-state, and transient success feedback
without introducing a framework. Errors that require a decision still use a
modal dialog; toasts are only for acknowledged-free success and information.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from app.core import constants
from app.ui.themes.tokens import METRICS

STATUS_NAMES = {
    "pass": "Success",
    "warning": "Warning",
    "error": "Error",
    "info": "Information",
}

_TOAST_TONE_COLORS = {
    "pass": "success",
    "warning": "warning",
    "error": "danger",
    "info": "info",
}


def apply_status(label: QLabel, tone: str, *, prefix: bool = False) -> None:
    """Apply a semantic tone to a label and give it a non-color accessible name.

    ``checkStatus`` drives border shape and color in the shared QSS; the
    accessible name keeps the meaning available to assistive technology.
    """
    if tone not in STATUS_NAMES:
        raise ValueError(f"unknown status tone: {tone!r}")
    if prefix and label.text() and not label.text().startswith(f"{STATUS_NAMES[tone]}:"):
        label.setText(f"{STATUS_NAMES[tone]}: {label.text()}")
    label.setProperty("checkStatus", tone)
    label.setAccessibleName(f"{STATUS_NAMES[tone]}: {label.text()}")
    style = label.style()
    if style is not None:
        style.unpolish(label)
        style.polish(label)


class StatusBadge(QLabel):
    """A short status message with a shape, a color, and an accessible name."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("MetaLabel")
        self.setWordWrap(True)
        self._tone = "info"
        apply_status(self, self._tone)

    @property
    def tone(self) -> str:
        return self._tone

    def set_status(self, text: str, tone: str = "info") -> None:
        self.setText(text)
        apply_status(self, tone)
        self._tone = tone


class EmptyState(QWidget):
    """Text-only empty state, as specified by the UI blueprint."""

    def __init__(
        self,
        title: str,
        detail: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyState")
        self.setAccessibleName(title)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_6, METRICS.space_5, METRICS.space_6, METRICS.space_5
        )
        layout.setSpacing(METRICS.space_2)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("SectionTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.detail_label = QLabel(detail, self)
        self.detail_label.setObjectName("MetaLabel")
        self.detail_label.setWordWrap(True)
        self.detail_label.setVisible(bool(detail))
        layout.addWidget(self.detail_label)
        layout.addStretch(1)


class Toast(QFrame):
    """Non-modal, auto-dismissing status message anchored to its parent."""

    def __init__(self, parent: QWidget, message: str, tone: str = "pass") -> None:
        super().__init__(parent)
        if tone not in _TOAST_TONE_COLORS:
            raise ValueError(f"unknown toast tone: {tone!r}")
        self.setObjectName("Toast")
        self.setProperty("card", True)
        self.setProperty("tone", tone)
        self.setAccessibleName(f"{STATUS_NAMES[tone]}: {message}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_3, METRICS.space_2, METRICS.space_3, METRICS.space_2
        )
        label = QLabel(message, self)
        label.setWordWrap(True)
        label.setMaximumWidth(METRICS.max_form_width)
        label.setAccessibleName(f"{STATUS_NAMES[tone]}: {message}")
        layout.addWidget(label)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.close()
        super().mousePressEvent(event)


def show_toast(parent: QWidget, message: str, *, tone: str = "pass") -> Toast:
    """Show a bottom-right toast, keeping at most two stacked toasts."""
    existing = [
        child
        for child in parent.findChildren(Toast)
        if child.parent() is parent and child.isVisible()
    ]
    for old in existing[:-1]:
        old.close()
        old.deleteLater()

    toast = Toast(parent, message, tone)
    toast.show()
    margin = METRICS.space_4
    position = QPoint(
        max(0, parent.width() - toast.width() - margin),
        max(0, parent.height() - toast.height() - margin),
    )
    toast.move(position)
    toast.raise_()
    QTimer.singleShot(constants.TOAST_DURATION_MS, toast.close)
    return toast


__all__ = ["EmptyState", "StatusBadge", "Toast", "apply_status", "show_toast"]
