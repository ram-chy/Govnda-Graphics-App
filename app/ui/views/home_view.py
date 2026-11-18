"""Dashboard presentation for the desktop shell.

It reports only facts the application has actually verified. No business
metrics, sample transactions, or placeholder financial data are shown.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from app.core import constants
from app.core.config import AppConfig
from app.core.formatting import format_money
from app.ui.components.cards import SectionCard
from app.ui.components.controls import DetailCard
from app.ui.components.feedback import EmptyState, StatusBadge
from app.ui.themes.tokens import METRICS


class HomeView(QWidget):
    """Static status screen for the verified foundation phases."""

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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget(scroll)
        content.setObjectName("DashboardContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_5)

        status_card = SectionCard("Application foundation", content)
        badge = StatusBadge("", status_card)
        if database_path is None:
            badge.set_status("Setup required", "warning")
            status_card.add_widget(badge)
            status_card.add_body(
                "The desktop shell, configuration service, logging, theme switching, "
                "and INR currency formatting are active. No business data location "
                "has been configured yet."
            )
        else:
            badge.set_status("Verified and ready", "pass")
            status_card.add_widget(badge)
            status_card.add_body(
                "The desktop shell, configuration service, logging, theme switching, "
                "and INR currency formatting are active. The SQLite business database "
                "was verified at startup."
            )
        layout.addWidget(status_card)

        details = DetailCard("Environment", content)
        details.add_row("Version", constants.APP_VERSION)
        details.add_row(
            "Default currency",
            f"{config.currency.code}  {config.currency.symbol}",
        )
        details.add_row(
            "Formatting example",
            format_money(Decimal("1250.50"), config.currency),
        )
        if database_path is None:
            details.add_row(
                "Data location",
                "Not configured - start the application normally to run first-launch setup.",
            )
        else:
            details.add_row(
                "Data location",
                str(data_root) if data_root is not None else str(database_path.parent),
            )
            details.add_row("Database file", str(database_path))
        layout.addWidget(details)

        storage_card = SectionCard("Business database", content)
        if database_path is None:
            storage_card.add_body(
                "The live database is created only by the first-launch setup wizard. "
                "The application never invents a path and never creates a fallback "
                "database."
            )
        else:
            storage_card.add_body(
                "Startup verification checks the file identity, schema revision, and "
                "SQLite header before the business interface opens."
            )
        layout.addWidget(storage_card)

        records_card = SectionCard("Business records", content)
        records_card.add_widget(
            EmptyState(
                "No business records are available yet",
                "Sales, purchases, inventory, and accounting modules are not part of this "
                "build. Summary values appear only after those modules and their approved "
                "report definitions are released.",
                records_card,
            )
        )
        layout.addWidget(records_card)
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)


__all__ = ["HomeView"]
