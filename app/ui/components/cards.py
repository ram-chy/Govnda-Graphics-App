"""Shared card container used by dashboard and placeholder screens."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from app.ui.themes.tokens import METRICS


class SectionCard(QFrame):
    """A titled surface that groups related content."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_5,
            METRICS.space_4,
            METRICS.space_5,
            METRICS.space_5,
        )
        layout.setSpacing(METRICS.space_2)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("SectionTitle")
        layout.addWidget(self.title_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(METRICS.space_2)
        layout.addLayout(self.content_layout)

    def add_widget(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)

    def add_body(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setWordWrap(True)
        self.content_layout.addWidget(label)
        return label
