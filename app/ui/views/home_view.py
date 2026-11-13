"""Phase 1 dashboard foundation."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from app.core import constants
from app.core.config import AppConfig
from app.core.formatting import format_money
from app.ui.components.cards import SectionCard
from app.ui.themes.tokens import METRICS


class HomeView(QWidget):
    """Static foundation status screen.

    It reports verified Phase 1 facts only. No business metrics, sample
    transactions, or placeholder financial data are shown.
    """

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
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

        status_card = SectionCard("Application foundation is running", self)
        status_card.add_body(
            "The desktop shell, configuration service, logging, theme switching, "
            "and INR currency formatting are active. Business modules and the "
            "database layer are intentionally not part of this phase."
        )
        layout.addWidget(status_card)

        details = QGridLayout()
        details.setHorizontalSpacing(METRICS.space_4)
        details.setVerticalSpacing(METRICS.space_4)

        details.addWidget(self._info_card("Version", constants.APP_VERSION), 0, 0)
        details.addWidget(
            self._info_card(
                "Default currency",
                f"{config.currency.code}  {config.currency.symbol}",
                f"Example: {format_money(Decimal('1250.50'), config.currency)}",
            ),
            0,
            1,
        )
        details.addWidget(
            self._info_card("Storage mode", "Local and offline", "No database configured yet"),
            0,
            2,
        )
        details.setColumnStretch(0, 1)
        details.setColumnStretch(1, 1)
        details.setColumnStretch(2, 1)
        layout.addLayout(details)

        next_card = SectionCard("Next phase", self)
        next_card.add_body(
            "Phase 2 adds the SQLite database, SQLAlchemy engine, and Alembic "
            "migration foundation. Business data will not be created until the "
            "setup and backup phases are complete."
        )
        layout.addWidget(next_card)
        layout.addStretch(1)

    def _info_card(self, label: str, value: str, meta: str = "") -> SectionCard:
        card = SectionCard(label, self)
        value_label = QLabel(value, card)
        value_label.setObjectName("KpiValue")
        card.add_widget(value_label)
        if meta:
            meta_label = QLabel(meta, card)
            meta_label.setObjectName("MetaLabel")
            meta_label.setWordWrap(True)
            card.add_widget(meta_label)
        return card


__all__ = ["HomeView"]
