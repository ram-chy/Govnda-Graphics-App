"""Reusable placeholder for modules scheduled for later phases."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.components.cards import SectionCard
from app.ui.themes.tokens import METRICS


class PlaceholderView(QWidget):
    """Honest empty state for a module that is not implemented yet.

    A single reusable widget is used for every future module so the project
    does not accumulate empty per-module modules or fake screens.
    """

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentArea")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_5)

        card = SectionCard(f"{title} is not available yet", self)
        card.add_body(
            "This area is reserved for a later development phase. "
            "No business functionality is implemented in the current build."
        )
        if subtitle:
            meta = QLabel(subtitle, card)
            meta.setObjectName("MetaLabel")
            meta.setWordWrap(True)
            card.add_widget(meta)

        layout.addWidget(card)
        layout.addStretch(1)
