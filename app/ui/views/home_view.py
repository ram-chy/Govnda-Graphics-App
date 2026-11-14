"""Dashboard foundation for the desktop shell."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from app.core import constants
from app.core.config import AppConfig
from app.core.formatting import format_money
from app.ui.components.cards import SectionCard
from app.ui.themes.tokens import METRICS


class HomeView(QWidget):
    """Static status screen for the verified foundation phases.

    It reports only facts the application has actually verified. No business
    metrics, sample transactions, or placeholder financial data are shown.
    """

    def __init__(
        self,
        config: AppConfig,
        parent: QWidget | None = None,
        *,
        database_path: Path | None = None,
        data_root: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContentArea")
        self._database_path = database_path
        self._data_root = data_root

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_5)

        status_card = SectionCard("Application foundation is running", self)
        if database_path is None:
            status_card.add_body(
                "The desktop shell, configuration service, logging, theme switching, "
                "and INR currency formatting are active. No business data location "
                "has been configured yet."
            )
        else:
            status_card.add_body(
                "The desktop shell, configuration service, logging, theme switching, "
                "and INR currency formatting are active. The SQLite business database "
                "was verified at startup."
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
        if database_path is None:
            details.addWidget(
                self._info_card(
                    "Data location",
                    "Not configured",
                    "Start the application normally to run first-launch setup.",
                ),
                0,
                2,
            )
        else:
            details.addWidget(
                self._info_card(
                    "Data location",
                    "Configured",
                    str(data_root) if data_root is not None else str(database_path.parent),
                ),
                0,
                2,
            )
        details.setColumnStretch(0, 1)
        details.setColumnStretch(1, 1)
        details.setColumnStretch(2, 1)
        layout.addLayout(details)

        storage_card = SectionCard("Business database", self)
        if database_path is None:
            storage_card.add_body(
                "The live database is created only by the first-launch setup wizard. "
                "The application never invents a path and never creates a fallback "
                "database."
            )
        else:
            storage_card.add_body(f"Database file: {database_path}")
            storage_card.add_body(
                "Startup verification checks the file identity, schema revision, and "
                "SQLite header before the business interface opens."
            )
        layout.addWidget(storage_card)

        next_card = SectionCard("Next phase", self)
        next_card.add_body(
            "Phase 4 adds verified safety backups, restore, and the backup schedule. "
            "Business modules remain intentionally unavailable until their phases."
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
