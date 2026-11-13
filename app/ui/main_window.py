"""Main application window and navigation shell."""

from __future__ import annotations

import logging

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.ui.components.placeholder_view import PlaceholderView
from app.ui.components.sidebar import NavGroup, NavItem, Sidebar
from app.ui.components.top_bar import TopBar
from app.ui.themes.manager import ThemeManager
from app.ui.viewmodels.shell_viewmodel import ShellViewModel
from app.ui.views.home_view import HomeView

logger = logging.getLogger(__name__)

NAVIGATION_GROUPS: tuple[NavGroup, ...] = (
    NavGroup(
        title="Overview",
        items=(
            NavItem("dashboard", "Dashboard", "Foundation build - no business data yet"),
        ),
    ),
    NavGroup(
        title="Operations",
        items=(
            NavItem("sales", "Sales", "Invoices, payments and balances - Phase 8"),
            NavItem("purchases", "Purchases", "Supplier bills and payments - Phase 8"),
            NavItem("inventory", "Inventory", "Stock movements and valuation - Phase 8"),
        ),
    ),
    NavGroup(
        title="Parties",
        items=(
            NavItem("customers", "Customers", "Customer records and statements - Phase 7"),
            NavItem("suppliers", "Suppliers", "Supplier records and balances - Phase 7"),
        ),
    ),
    NavGroup(
        title="Finance",
        items=(
            NavItem("expenses", "Expenses", "Expense recording and categories - Phase 9"),
            NavItem("accounting", "Accounting", "Ledgers and financial summaries - Phase 9"),
            NavItem("reports", "Reports", "PDF and Excel exports - Phase 10"),
        ),
    ),
    NavGroup(
        title="System",
        items=(
            NavItem("settings", "Settings", "Business profile and preferences - Phase 7"),
            NavItem("backup", "Backup", "Backup, restore and schedule - Phase 4"),
        ),
    ),
)

_NAV_ITEMS: dict[str, NavItem] = {
    item.key: item for group in NAVIGATION_GROUPS for item in group.items
}


class MainWindow(QMainWindow):
    """Application shell: sidebar, top bar, content area, and status bar."""

    def __init__(
        self,
        viewmodel: ShellViewModel,
        theme_manager: ThemeManager,
        *,
        app_version: str = constants.APP_VERSION,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._theme_manager = theme_manager
        self._views: dict[str, QWidget] = {}
        self._current_key = ""

        self.setWindowTitle(constants.APP_NAME)
        self.resize(1440, 900)
        self.setMinimumSize(1280, 720)

        self._build_ui(app_version)

        self._theme_manager.changed.connect(self._on_theme_changed)
        self._theme_manager.apply(self._viewmodel.theme_preference)
        self.navigate("dashboard")
        self._center_on_primary_screen()

    @property
    def viewmodel(self) -> ShellViewModel:
        return self._viewmodel

    @property
    def sidebar(self) -> Sidebar:
        return self._sidebar

    @property
    def top_bar(self) -> TopBar:
        return self._top_bar

    @property
    def content_stack(self) -> QStackedWidget:
        return self._stack

    @property
    def theme_manager(self) -> ThemeManager:
        return self._theme_manager

    @property
    def current_key(self) -> str:
        return self._current_key

    def navigate(self, key: str) -> None:
        """Show the view for ``key``, creating it lazily on first use."""
        try:
            item = _NAV_ITEMS[key]
        except KeyError as exc:
            raise KeyError(f"unknown navigation key: {key!r}") from exc

        view = self._views.get(key)
        if view is None:
            view = self._create_view(key, item)
            self._views[key] = view
            self._stack.addWidget(view)

        self._stack.setCurrentWidget(view)
        self._top_bar.set_page(item.label, item.subtitle)
        self._sidebar.set_active(key)
        self._current_key = key
        logger.info("Navigated to %s", key)

    def closeEvent(self, event: QCloseEvent) -> None:
        logger.info("Main window closing")
        super().closeEvent(event)

    def _build_ui(self, app_version: str) -> None:
        central = QWidget(self)
        central.setObjectName("CentralWidget")
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._sidebar = Sidebar(NAVIGATION_GROUPS, central)
        self._sidebar.navigation_requested.connect(self.navigate)
        root_layout.addWidget(self._sidebar)

        content_area = QWidget(central)
        content_area.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._top_bar = TopBar(content_area)
        self._top_bar.theme_toggle_requested.connect(self._toggle_theme)
        content_layout.addWidget(self._top_bar)

        self._stack = QStackedWidget(content_area)
        content_layout.addWidget(self._stack, 1)

        root_layout.addWidget(content_area, 1)
        self.setCentralWidget(central)

        self._build_status_bar(app_version)
        self._viewmodel.status_message_changed.connect(self._show_status_message)

    def _build_status_bar(self, app_version: str) -> None:
        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.showMessage("Ready")

        database_status = QLabel("Database: not configured", status)
        database_status.setToolTip("Database storage will be configured in a later phase.")
        status.addPermanentWidget(database_status)

        currency = self._viewmodel.currency
        currency_status = QLabel(f"{currency.code} {currency.symbol}", status)
        currency_status.setToolTip("Default currency used for display formatting.")
        status.addPermanentWidget(currency_status)

        offline_status = QLabel("Local only", status)
        offline_status.setToolTip("This application works fully offline.")
        status.addPermanentWidget(offline_status)

        version_status = QLabel(f"v{app_version}", status)
        version_status.setToolTip(constants.APP_NAME)
        status.addPermanentWidget(version_status)

    def _create_view(self, key: str, item: NavItem) -> QWidget:
        if key == "dashboard":
            return HomeView(self._viewmodel.config, self)
        return PlaceholderView(item.label, item.subtitle, self)

    def _toggle_theme(self) -> None:
        new_mode = self._theme_manager.toggle()
        self._viewmodel.set_theme_preference(new_mode.value)

    def _on_theme_changed(self, _preference: str, is_dark: bool) -> None:
        self._top_bar.set_theme(is_dark=is_dark)

    def _show_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)

    def _center_on_primary_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.availableGeometry().center())
        self.move(geometry.topLeft())


__all__ = ["MainWindow", "NAVIGATION_GROUPS"]
