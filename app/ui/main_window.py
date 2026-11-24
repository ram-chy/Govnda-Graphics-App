"""Main application window and navigation shell."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.core.config import ConfigService
from app.domain.auth import SESSION_ENTITY_TYPE, AuthEventType, actor_for_user
from app.domain.catalogue import CatalogueKind
from app.domain.party import PartyKind
from app.services.auth_services import AuthServices
from app.services.auth_support import actor_payload
from app.services.backup_workspace import BackupWorkspaceFactory
from app.services.business_profile_service import BusinessProfileServiceFactory
from app.services.catalogue_service import CatalogueServiceFactory
from app.services.database_runtime import DatabaseRuntime
from app.services.party_service import PartyServiceFactory
from app.ui.components.placeholder_view import PlaceholderView
from app.ui.components.sidebar import NavGroup, NavItem, Sidebar
from app.ui.components.top_bar import TopBar
from app.ui.dialogs.auth_dialogs import (
    LockDialog,
    LoginDialog,
    PasswordChangeDialog,
    UserManagementDialog,
)
from app.ui.formatting import format_backup_time
from app.ui.themes.manager import ThemeManager
from app.ui.themes.tokens import METRICS
from app.ui.viewmodels.backup_viewmodel import BackupSnapshot, BackupViewModel
from app.ui.viewmodels.business_profile_viewmodel import BusinessProfileViewModel
from app.ui.viewmodels.catalogue_viewmodel import CatalogueViewModel
from app.ui.viewmodels.party_viewmodel import PartyViewModel
from app.ui.viewmodels.shell_viewmodel import ShellViewModel
from app.ui.views.backup_view import BackupView
from app.ui.views.business_profile_view import BusinessProfileView
from app.ui.views.catalogue_view import CatalogueView
from app.ui.views.home_view import HomeView
from app.ui.views.party_view import PartyView

logger = logging.getLogger(__name__)

NAVIGATION_GROUPS: tuple[NavGroup, ...] = (
    NavGroup(
        title="Overview",
        items=(NavItem("dashboard", "Dashboard", "Foundation build - no business data yet"),),
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
        title="Catalogue",
        items=(
            NavItem("products", "Products", "Product catalogue records - Phase 10"),
            NavItem("services", "Services", "Service catalogue records - Phase 10"),
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
            NavItem("settings", "Settings", "Business profile and application preferences"),
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
        database_path: Path | None = None,
        data_root: Path | None = None,
        config_service: ConfigService | None = None,
        database_runtime: DatabaseRuntime | None = None,
        workspace_factory: BackupWorkspaceFactory | None = None,
        business_profile_factory: BusinessProfileServiceFactory | None = None,
        party_factory: PartyServiceFactory | None = None,
        catalogue_factory: CatalogueServiceFactory | None = None,
        auth_services: AuthServices | None = None,
        settings: QSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._theme_manager = theme_manager
        self._settings = settings or QSettings(
            constants.ORGANIZATION_NAME, constants.APP_SHORT_NAME
        )
        self._session_restored = False
        self._database_path = database_path
        self._data_root = data_root
        self._views: dict[str, QWidget] = {}
        self._current_key = ""
        self._backup_viewmodel: BackupViewModel | None = None
        self._backup_status: QLabel | None = None
        self._business_profile_viewmodel: BusinessProfileViewModel | None = None
        self._party_factory = party_factory
        self._catalogue_factory = catalogue_factory
        self._auth_services = auth_services
        self._lock_dialog: LockDialog | None = None
        if business_profile_factory is not None:
            self._business_profile_viewmodel = BusinessProfileViewModel(
                business_profile_factory, parent=self
            )
            self._business_profile_viewmodel.status_message.connect(self._show_status_message)
        if (
            config_service is not None
            and database_runtime is not None
            and workspace_factory is not None
        ):
            self._backup_viewmodel = BackupViewModel(
                workspace_factory,
                config_service,
                database_runtime,
                parent=self,
            )

        self.setWindowTitle(constants.APP_NAME)
        self.resize(METRICS.window_default_width, METRICS.window_default_height)
        self.setMinimumSize(METRICS.window_minimum_width, METRICS.window_minimum_height)

        self._build_ui(app_version)
        if self._backup_viewmodel is not None:
            self._backup_viewmodel.status_message.connect(self._show_status_message)
            self._backup_viewmodel.database_changed.connect(self._on_database_changed)
            self._backup_viewmodel.snapshot_changed.connect(self._on_backup_snapshot)

        self._theme_manager.changed.connect(self._on_theme_changed)
        self._theme_manager.apply(self._viewmodel.theme_preference)
        self._setup_shortcuts()
        geometry_restored = self._restore_geometry()
        self._session_restored = True
        self._install_idle_monitor()

        saved_key = self._settings.value("navigation/current", "dashboard", type=str)
        self.navigate(saved_key if saved_key in _NAV_ITEMS else "dashboard")
        if not geometry_restored:
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
        if self._session_restored:
            self._settings.setValue("navigation/current", key)
        logger.info("Navigated to %s", key)

    def _install_idle_monitor(self) -> None:
        if self._auth_services is None:
            return
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(30_000)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        self._idle_timer.start()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802 - Qt API
        active_events = {
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchEnd,
        }
        if (
            self._auth_services is not None
            and event.type() in active_events
            and not self._auth_services.session.is_locked
        ):
            self._auth_services.session.touch()
        return super().eventFilter(watched, event)

    def _on_idle_tick(self) -> None:
        if self._auth_services is None:
            return
        session = self._auth_services.session
        if session.should_lock() and self._lock_dialog is None and session.lock():
            identity = session.identity
            if identity is not None:
                self._auth_services.audit.record(
                    event_type=AuthEventType.LOCK,
                    entity_type=SESSION_ENTITY_TYPE,
                    entity_id=str(identity.user_id),
                    actor=actor_for_user(identity.user_id, identity.username),
                    payload=actor_payload(session),
                )
            self._show_lock_dialog()

    def _show_lock_dialog(self) -> None:
        if self._auth_services is None or self._lock_dialog is not None:
            return
        dialog = LockDialog(self._auth_services, self)
        self._lock_dialog = dialog
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        try:
            result = dialog.exec()
        finally:
            self._lock_dialog = None
        if result == QDialog.DialogCode.Accepted:
            self._sync_account_ui()
            return
        if getattr(dialog, "exit_requested", False):
            # Closing while locked ends the session without exposing data.
            self._auth_services.session.end()
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return
        if self._auth_services.session.is_locked:
            # A locked session must not expose the application.
            self._show_lock_dialog()
            return
        if self._auth_services.session.identity is None:
            login = LoginDialog(self._auth_services.authentication, self)
            if login.exec() != QDialog.DialogCode.Accepted:
                app = QApplication.instance()
                if app is not None:
                    app.quit()
                return
            self._sync_account_ui()

    def _sync_account_ui(self) -> None:
        auth = self._auth_services
        if auth is None:
            return
        identity = auth.session.identity
        authenticated = identity is not None and not auth.session.is_locked
        self._top_bar.user_button.setVisible(
            authenticated and auth.authorization.has_permission("user.edit_identity")
        )
        self._top_bar.password_button.setVisible(
            authenticated and auth.authorization.has_permission("auth.password_change_self")
        )
        self._top_bar.logout_button.setVisible(
            authenticated and auth.authorization.has_permission("auth.logout")
        )
        if hasattr(self, "_session_status"):
            if identity is None:
                self._session_status.setText("Signed out")
            else:
                self._session_status.setText(f"User: {identity.username}")

    def _open_user_management(self) -> None:
        if self._auth_services is None:
            return
        dialog = UserManagementDialog(self._auth_services, self)
        dialog.exec()
        self._sync_account_ui()

    def _open_change_password(self) -> None:
        if self._auth_services is None:
            return
        dialog = PasswordChangeDialog(self._auth_services, self)
        dialog.exec()
        self._sync_account_ui()

    def _logout(self) -> None:
        if self._auth_services is None:
            return
        self._auth_services.authentication.logout()
        self._sync_account_ui()
        login = LoginDialog(self._auth_services.authentication, self)
        if login.exec() != QDialog.DialogCode.Accepted:
            QApplication.instance().quit() if QApplication.instance() is not None else None
            return
        self._sync_account_ui()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._backup_viewmodel is not None and self._backup_viewmodel.is_busy:
            logger.info("Close requested while a backup operation is running")
            QMessageBox.warning(
                self,
                "A backup operation is still running",
                "Wait for the current backup, restore, relocation, or schedule change to "
                "finish before closing the application. The operation is protected by a "
                "cross-process lock and cannot be cancelled safely.",
            )
            event.ignore()
            return
        if self._auth_services is not None and self._auth_services.session.is_locked:
            self._auth_services.session.end()
        self._save_session()
        logger.info("Main window closing")
        if self._backup_viewmodel is not None:
            self._backup_viewmodel.shutdown()
        super().closeEvent(event)

    def run_startup_catch_up(self) -> bool:
        """Run one missed-backup check if the backup workspace is available."""
        if self._backup_viewmodel is None:
            logger.info("Startup catch-up skipped: backup workspace is unavailable")
            return False
        return self._backup_viewmodel.run_startup_catch_up()

    def _setup_shortcuts(self) -> None:
        """Provide keyboard refresh for the active page."""
        self._refresh_shortcut = QShortcut(QKeySequence.StandardKey.Refresh, self)
        self._refresh_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._refresh_shortcut.setWhatsThis("Refresh the current page")
        self._refresh_shortcut.activated.connect(self._refresh_current_view)

    def _refresh_current_view(self) -> None:
        widget = self._stack.currentWidget()
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()

    def _restore_geometry(self) -> bool:
        """Restore geometry and state only when they fit a connected screen."""
        raw_geometry = self._settings.value("window/geometry")
        if not isinstance(raw_geometry, (bytes, QByteArray)) or not raw_geometry:
            return False
        if not self.restoreGeometry(QByteArray(raw_geometry)):
            return False
        screen = QApplication.screenAt(self.geometry().center())
        available = screen.availableGeometry() if screen is not None else None
        if available is None:
            return False
        if self.width() > available.width() or self.height() > available.height():
            return False

        raw_state = self._settings.value("window/state")
        if isinstance(raw_state, (bytes, QByteArray)) and raw_state:
            self.restoreState(QByteArray(raw_state))
        return True

    def _save_session(self) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        self._settings.setValue("navigation/current", self._current_key)

    def _on_backup_snapshot(self, snapshot: object) -> None:
        if self._backup_status is None:
            return
        assert isinstance(snapshot, BackupSnapshot)
        if not snapshot.available:
            self._backup_status.setText("Backup: unavailable")
            self._backup_status.setToolTip(snapshot.unavailable_reason)
            return
        latest = snapshot.latest_verified()
        if latest is None:
            self._backup_status.setText("Backup: none verified")
            self._backup_status.setToolTip("No verified backup has been recorded yet.")
            return
        created = format_backup_time(latest.created_at_utc, fallback="Unknown")
        self._backup_status.setText(f"Backup: {created}")
        self._backup_status.setToolTip(f"Verified backup: {latest.file_name}")

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
        self._top_bar.user_management_requested.connect(self._open_user_management)
        self._top_bar.change_password_requested.connect(self._open_change_password)
        self._top_bar.logout_requested.connect(self._logout)
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
        status.setAccessibleName("Application status")
        status.showMessage("Ready")

        if self._database_path is None:
            self._database_status = QLabel("Database: not configured", status)
            self._database_status.setToolTip(
                "The business data location is recorded by the first-launch setup wizard."
            )
        else:
            self._database_status = QLabel("Database: configured", status)
            self._database_status.setToolTip(str(self._database_path))
        self._database_status.setAccessibleName("Database status")
        status.addPermanentWidget(self._database_status)

        if self._backup_viewmodel is not None:
            self._backup_status = QLabel("Backup: not checked", status)
            self._backup_status.setAccessibleName("Last verified backup")
            self._backup_status.setToolTip("Open Backup to review the verified backup history.")
            status.addPermanentWidget(self._backup_status)

        self._session_status = QLabel("Signed out", status)
        self._session_status.setAccessibleName("Current user")
        status.addPermanentWidget(self._session_status)

        currency = self._viewmodel.currency
        currency_status = QLabel(f"{currency.code} {currency.symbol}", status)
        currency_status.setToolTip("Default currency used for display formatting.")
        currency_status.setAccessibleName("Default currency")
        status.addPermanentWidget(currency_status)

        offline_status = QLabel("Local only", status)
        offline_status.setToolTip("This application works fully offline.")
        offline_status.setAccessibleName("Local-only operation")
        status.addPermanentWidget(offline_status)

        version_status = QLabel(f"v{app_version}", status)
        version_status.setToolTip(constants.APP_NAME)
        version_status.setAccessibleName(f"Version {app_version}")
        status.addPermanentWidget(version_status)

        self._sync_account_ui()

    def _create_view(self, key: str, item: NavItem) -> QWidget:
        if key == "dashboard":
            return self._build_home_view()
        if key == "backup" and self._backup_viewmodel is not None:
            return BackupView(self._backup_viewmodel, self, auth_services=self._auth_services)
        if key == "settings" and self._business_profile_viewmodel is not None:
            return BusinessProfileView(self._business_profile_viewmodel, self)
        if key in {"customers", "suppliers"} and self._party_factory is not None:
            kind = PartyKind.CUSTOMER if key == "customers" else PartyKind.SUPPLIER
            vm = PartyViewModel(kind, self._party_factory, parent=self)
            vm.status_message.connect(self._show_status_message)
            return PartyView(vm, self)
        if key in {"products", "services"} and self._catalogue_factory is not None:
            kind = CatalogueKind.PRODUCT if key == "products" else CatalogueKind.SERVICE
            vm = CatalogueViewModel(kind, self._catalogue_factory, parent=self)
            vm.status_message.connect(self._show_status_message)
            return CatalogueView(vm, self)
        return PlaceholderView(item.label, item.subtitle, self)

    def _build_home_view(self) -> HomeView:
        return HomeView(
            self._viewmodel.config,
            self,
            database_path=self._database_path,
            data_root=self._data_root,
        )

    def _on_database_changed(self, data_root: str, database_path: str) -> None:
        """Reflect a completed restore or relocation in every open surface."""
        self._data_root = Path(data_root)
        self._database_path = Path(database_path)
        self._database_status.setText("Database: configured")
        self._database_status.setToolTip(database_path)
        self.statusBar().showMessage(
            f"Database location: {database_path}", constants.DATABASE_MESSAGE_TIMEOUT_MS
        )
        self._replace_dashboard()
        self._replace_business_profile()

    def _replace_dashboard(self) -> None:
        previous = self._views.get("dashboard")
        if previous is None:
            return
        was_current = self._stack.currentWidget() is previous
        self._stack.removeWidget(previous)
        previous.deleteLater()
        replacement = self._build_home_view()
        self._views["dashboard"] = replacement
        self._stack.addWidget(replacement)
        if was_current:
            self._stack.setCurrentWidget(replacement)

    def _replace_business_profile(self) -> None:
        if self._business_profile_viewmodel is None:
            return
        previous = self._views.get("settings")
        if previous is None or not isinstance(previous, BusinessProfileView):
            return
        was_current = self._stack.currentWidget() is previous
        self._stack.removeWidget(previous)
        previous.deleteLater()
        replacement = BusinessProfileView(self._business_profile_viewmodel, self)
        self._views["settings"] = replacement
        self._stack.addWidget(replacement)
        if was_current:
            self._stack.setCurrentWidget(replacement)

    def _toggle_theme(self) -> None:
        new_mode = self._theme_manager.toggle()
        self._viewmodel.set_theme_preference(new_mode.value)

    def _on_theme_changed(self, _preference: str, is_dark: bool) -> None:
        self._top_bar.set_theme(is_dark=is_dark)

    def _show_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, constants.STATUS_MESSAGE_TIMEOUT_MS)

    def _center_on_primary_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.availableGeometry().center())
        self.move(geometry.topLeft())


__all__ = ["MainWindow", "NAVIGATION_GROUPS"]
