"""Native authentication, session, and local-account dialogs."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.core.exceptions import AppError
from app.domain.auth import (
    ROLE_DISPLAY_NAMES,
    PermissionKey,
    RoleKey,
    UserAccount,
)
from app.services.auth_services import AuthServices
from app.ui.components.controls import make_button, set_dialog_size
from app.ui.components.feedback import StatusBadge
from app.ui.themes.tokens import METRICS

_ROLE_ITEMS: tuple[tuple[str, RoleKey], ...] = tuple(
    (ROLE_DISPLAY_NAMES[role], role) for role in RoleKey
)


def _password_field(parent: QWidget, *, placeholder: str = "") -> QLineEdit:
    field = QLineEdit(parent)
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    field.setClearButtonEnabled(False)
    field.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return field


def _set_status(status: StatusBadge, message: str, *, tone: str = "info") -> None:
    status.set_status(message, tone)


class _CredentialDialog(QDialog):
    """Base class that never retains typed passwords after an attempt."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AuthDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        set_dialog_size(
            self,
            METRICS.dialog_width,
            METRICS.dialog_height,
            minimum_width=METRICS.dialog_minimum_width,
            minimum_height=METRICS.dialog_minimum_height,
        )
        self._password_fields: list[QLineEdit] = []

    def _track_password(self, field: QLineEdit) -> QLineEdit:
        self._password_fields.append(field)
        return field

    def _clear_passwords(self) -> None:
        for field in self._password_fields:
            field.clear()


class FirstRunDialog(_CredentialDialog):
    """Create the initial Owner/Admin before any protected UI is shown."""

    def __init__(self, authentication: object, parent: QWidget | None = None) -> None:
        super().__init__(f"Create owner account - {constants.APP_SHORT_NAME}", parent)
        self._authentication = authentication

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_6, METRICS.space_6, METRICS.space_6, METRICS.space_6
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("First-run owner setup", self)
        title.setObjectName("WizardTitle")
        detail = QLabel(
            "Create the local Owner/Admin account for this installation. "
            "No default account exists and no business data is shown until setup is complete.",
            self,
        )
        detail.setObjectName("MetaLabel")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(METRICS.space_3)
        self.username = QLineEdit(self)
        self.username.setAccessibleName("Owner username")
        self.username.setPlaceholderText("At least 3 characters, no spaces")
        self.email = QLineEdit(self)
        self.email.setAccessibleName("Optional email address")
        self.password = self._track_password(_password_field(self))
        self.password.setAccessibleName("Owner password")
        self.confirmation = self._track_password(_password_field(self))
        self.confirmation.setAccessibleName("Confirm owner password")
        form.addRow("Username", self.username)
        form.addRow("Email (optional)", self.email)
        form.addRow("Password", self.password)
        form.addRow("Confirm password", self.confirmation)
        layout.addLayout(form)

        self.status = StatusBadge("", self)
        layout.addWidget(self.status)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancel", self, variant="secondary")
        cancel.setAccessibleName("Cancel first-run setup")
        create = make_button("Create owner", self, default=True)
        create.setAccessibleName("Create the initial owner account")
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self._create)
        buttons.addWidget(cancel)
        buttons.addWidget(create)
        layout.addLayout(buttons)

        self.username.setFocus()

    def _create(self) -> None:
        try:
            self._authentication.create_first_run_owner(
                self.username.text(),
                self.password.text(),
                email=self.email.text(),
                confirmation=self.confirmation.text(),
            )
        except AppError as exc:
            _set_status(self.status, exc.user_message, tone="error")
            self._clear_passwords()
            return
        self._clear_passwords()
        self.accept()


class LoginDialog(_CredentialDialog):
    """Native login screen shown before the main window is constructed."""

    def __init__(self, authentication: object, parent: QWidget | None = None) -> None:
        super().__init__(f"Sign in - {constants.APP_SHORT_NAME}", parent)
        self._authentication = authentication

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_6, METRICS.space_6, METRICS.space_6, METRICS.space_6
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("Sign in to your local account", self)
        title.setObjectName("WizardTitle")
        detail = QLabel(
            "Use the username and password created for this installation. "
            "Email is not a login identity.",
            self,
        )
        detail.setObjectName("MetaLabel")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(METRICS.space_3)
        self.username = QLineEdit(self)
        self.username.setAccessibleName("Username")
        self.password = self._track_password(_password_field(self))
        self.password.setAccessibleName("Password")
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        self.status = StatusBadge("", self)
        layout.addWidget(self.status)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        quit_button = make_button("Quit", self, variant="secondary")
        quit_button.setAccessibleName("Quit the application")
        sign_in = make_button("Sign in", self, default=True)
        sign_in.setAccessibleName("Sign in")
        quit_button.clicked.connect(self.reject)
        sign_in.clicked.connect(self._sign_in)
        buttons.addWidget(quit_button)
        buttons.addWidget(sign_in)
        layout.addLayout(buttons)

        self.username.setFocus()

    def _sign_in(self) -> None:
        result = self._authentication.authenticate(self.username.text(), self.password.text())
        self._clear_passwords()
        if result.success:
            self.accept()
            return
        _set_status(self.status, result.message, tone="error")


class LockDialog(_CredentialDialog):
    """Application-modal unlock screen for the locked-in user."""

    def __init__(self, services: AuthServices, parent: QWidget | None = None) -> None:
        super().__init__(f"Session locked - {constants.APP_SHORT_NAME}", parent)
        self._services = services
        self.exit_requested = False
        self._allow_close = False
        identity = services.session.identity
        label = identity.username if identity is not None else "this account"
        role = services.session.role_key
        role_label = ROLE_DISPLAY_NAMES.get(role, "") if role is not None else ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_6, METRICS.space_6, METRICS.space_6, METRICS.space_6
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("The application is locked", self)
        title.setObjectName("WizardTitle")
        detail = QLabel(
            f"Enter the password for {label} to resume this session. "
            "Business data is not available while the session is locked.",
            self,
        )
        detail.setObjectName("MetaLabel")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        if role_label:
            role_tag = QLabel(f"Role: {role_label}", self)
            role_tag.setObjectName("MetaLabel")
            layout.addWidget(role_tag)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.password = self._track_password(_password_field(self))
        self.password.setAccessibleName("Password for the locked-in user")
        form.addRow("Password", self.password)
        layout.addLayout(form)

        self.status = StatusBadge("", self)
        layout.addWidget(self.status)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        exit_button = make_button("Exit application", self, variant="secondary")
        exit_button.setAccessibleName("Exit the application while locked")
        exit_button.clicked.connect(self._exit)
        buttons.addWidget(exit_button)
        unlock = make_button("Unlock", self, default=True)
        unlock.setAccessibleName("Unlock the session")
        unlock.clicked.connect(self._unlock)
        buttons.addWidget(unlock)
        layout.addLayout(buttons)

        self.password.setFocus()

    def _unlock(self) -> None:
        result = self._services.authentication.unlock(self.password.text())
        self._clear_passwords()
        if result.success:
            self.accept()
            return
        _set_status(self.status, result.message, tone="error")

    def _exit(self) -> None:
        """End the session through an explicit, accessible exit control."""

        self.exit_requested = True
        super().reject()

    def reject(self) -> None:  # noqa: N802 - Qt API
        # Esc must not silently dismiss the lock screen; use the explicit exit.
        return

    def closeEvent(self, event: QCloseEvent) -> None:
        # Closing the lock window ends the session rather than exposing data.
        self.exit_requested = True
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Escape,):
            event.ignore()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._unlock()
            return
        super().keyPressEvent(event)


class PasswordChangeDialog(_CredentialDialog):
    """Self-service password change with current-password verification."""

    def __init__(self, services: AuthServices, parent: QWidget | None = None) -> None:
        super().__init__("Change password", parent)
        self._services = services

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_6, METRICS.space_6, METRICS.space_6, METRICS.space_6
        )
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(METRICS.space_3)
        self.current = self._track_password(_password_field(self))
        self.current.setAccessibleName("Current password")
        self.new = self._track_password(_password_field(self))
        self.new.setAccessibleName("New password")
        self.confirmation = self._track_password(_password_field(self))
        self.confirmation.setAccessibleName("Confirm new password")
        form.addRow("Current password", self.current)
        form.addRow("New password", self.new)
        form.addRow("Confirm new password", self.confirmation)
        layout.addLayout(form)

        self.status = StatusBadge("", self)
        layout.addWidget(self.status)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancel", self, variant="secondary")
        change = make_button("Change password", self, default=True)
        cancel.clicked.connect(self.reject)
        change.clicked.connect(self._change)
        buttons.addWidget(cancel)
        buttons.addWidget(change)
        layout.addLayout(buttons)

        self.current.setFocus()

    def _change(self) -> None:
        try:
            self._services.passwords.change_self(
                self.current.text(), self.new.text(), self.confirmation.text()
            )
        except AppError as exc:
            _set_status(self.status, exc.user_message, tone="error")
            self._clear_passwords()
            return
        self._clear_passwords()
        _set_status(self.status, "Password changed.", tone="pass")
        QMessageBox.information(
            self,
            "Password changed",
            "Your password has been changed. No privileged re-authentication state was kept.",
        )
        self.accept()


class _RoleCombo(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        for label, role in _ROLE_ITEMS:
            self.addItem(label, role.value)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def role(self) -> RoleKey:
        return RoleKey(str(self.currentData()))


class _CreateUserDialog(_CredentialDialog):
    def __init__(self, services: AuthServices, parent: QWidget | None = None) -> None:
        super().__init__("Create local user", parent)
        self._services = services
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(METRICS.space_3)
        self.username = QLineEdit(self)
        self.username.setAccessibleName("New username")
        self.email = QLineEdit(self)
        self.email.setAccessibleName("New user email (optional)")
        self.password = self._track_password(_password_field(self))
        self.password.setAccessibleName("Initial password")
        self.confirmation = self._track_password(_password_field(self))
        self.confirmation.setAccessibleName("Confirm initial password")
        self.role = _RoleCombo(self)
        self.role.setAccessibleName("Role")
        form.addRow("Username", self.username)
        form.addRow("Email (optional)", self.email)
        form.addRow("Initial password", self.password)
        form.addRow("Confirm password", self.confirmation)
        form.addRow("Role", self.role)
        layout.addLayout(form)
        self.status = StatusBadge("", self)
        layout.addWidget(self.status)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancel", self, variant="secondary")
        create = make_button("Create user", self, default=True)
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self._create)
        buttons.addWidget(cancel)
        buttons.addWidget(create)
        layout.addLayout(buttons)

    def _create(self) -> None:
        try:
            self._services.users.create_user(
                self.username.text(),
                self.password.text(),
                self.role.role(),
                email=self.email.text(),
                confirmation=self.confirmation.text(),
            )
        except AppError as exc:
            _set_status(self.status, exc.user_message, tone="error")
            self._clear_passwords()
            return
        self._clear_passwords()
        self.accept()


class _EditUserDialog(QDialog):
    def __init__(self, account: UserAccount, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit user identity")
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.username = QLineEdit(account.username, self)
        self.username.setAccessibleName("Username")
        self.email = QLineEdit(account.email or "", self)
        self.email.setAccessibleName("Email (optional)")
        form.addRow("Username", self.username)
        form.addRow("Email (optional)", self.email)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancel", self, variant="secondary")
        save = make_button("Save", self, default=True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)


class _RoleDialog(QDialog):
    def __init__(self, account: UserAccount, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assign role")
        self.setModal(True)
        layout = QVBoxLayout(self)
        label = QLabel(f"Role for {account.username}", self)
        layout.addWidget(label)
        self.role = _RoleCombo(self)
        index = self.role.findData(account.role_key.value)
        if index >= 0:
            self.role.setCurrentIndex(index)
        layout.addWidget(self.role)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancel", self, variant="secondary")
        save = make_button("Assign", self, default=True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)


class _ResetPasswordDialog(_CredentialDialog):
    def __init__(self, account: UserAccount, parent: QWidget | None = None) -> None:
        super().__init__(f"Reset password - {account.username}", parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.password = self._track_password(_password_field(self))
        self.password.setAccessibleName("New password")
        self.confirmation = self._track_password(_password_field(self))
        self.confirmation.setAccessibleName("Confirm new password")
        form.addRow("New password", self.password)
        form.addRow("Confirm password", self.confirmation)
        layout.addLayout(form)
        self.status = StatusBadge("", self)
        layout.addWidget(self.status)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancel", self, variant="secondary")
        reset = make_button("Reset password", self, default=True)
        cancel.clicked.connect(self.reject)
        reset.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(reset)
        layout.addLayout(buttons)


class UserManagementDialog(QDialog):
    """Owner/Admin screen for approved local-account administration."""

    def __init__(self, services: AuthServices, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("UserManagementDialog")
        self.setWindowTitle("Local user accounts")
        self.setModal(True)
        set_dialog_size(
            self,
            METRICS.dialog_width,
            METRICS.dialog_height,
            minimum_width=METRICS.dialog_minimum_width,
            minimum_height=METRICS.dialog_minimum_height,
        )
        self._services = services

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            METRICS.space_5, METRICS.space_5, METRICS.space_5, METRICS.space_5
        )
        layout.setSpacing(METRICS.space_3)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Email", "Role", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAccessibleName("Local user accounts")
        layout.addWidget(self.table)

        self.status = StatusBadge("", self)
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.add_button = make_button("Add user", self)
        self.edit_button = make_button("Edit identity", self, variant="secondary")
        self.role_button = make_button("Assign role", self, variant="secondary")
        self.active_button = make_button("Deactivate", self, variant="secondary")
        self.reset_button = make_button("Reset password", self, variant="secondary")
        close_button = make_button("Close", self, variant="secondary")
        permissions = {
            self.add_button: PermissionKey.USER_CREATE,
            self.edit_button: PermissionKey.USER_EDIT_IDENTITY,
            self.role_button: PermissionKey.USER_ASSIGN_ROLE,
            self.active_button: None,
            self.reset_button: PermissionKey.USER_RESET_PASSWORD,
        }
        for button, permission in permissions.items():
            if permission is not None:
                button.setEnabled(self._services.authorization.has_permission(permission))
            else:
                button.setEnabled(
                    self._services.authorization.has_permission(PermissionKey.USER_ACTIVATE)
                    or self._services.authorization.has_permission(PermissionKey.USER_DEACTIVATE)
                )
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.add_button.clicked.connect(self._create_user)
        self.edit_button.clicked.connect(self._edit_user)
        self.role_button.clicked.connect(self._assign_role)
        self.active_button.clicked.connect(self._toggle_active)
        self.reset_button.clicked.connect(self._reset_password)
        close_button.clicked.connect(self.accept)

        self._refresh()

    def _refresh(self) -> None:
        try:
            accounts = self._services.users.list_users()
        except AppError as exc:
            _set_status(self.status, exc.user_message, tone="error")
            return
        self.table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            values = (
                str(account.user_id),
                account.username,
                account.email or "-",
                ROLE_DISPLAY_NAMES[account.role_key],
                "Active" if account.is_active else "Deactivated",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        _set_status(self.status, f"{len(accounts)} local account(s).", tone="info")

    def _selected(self) -> UserAccount | None:
        row = self.table.currentRow()
        if row < 0:
            _set_status(self.status, "Select an account first.", tone="warning")
            return None
        user_id = int(self.table.item(row, 0).text())
        try:
            return next(
                account
                for account in self._services.users.list_users()
                if account.user_id == user_id
            )
        except AppError, StopIteration:
            _set_status(self.status, "The selected account is unavailable.", tone="error")
            return None

    def _run(self, action: Callable[[], None]) -> None:
        try:
            action()
        except AppError as exc:
            _set_status(self.status, exc.user_message, tone="error")
            return
        self._refresh()

    def _create_user(self) -> None:
        dialog = _CreateUserDialog(self._services, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh()

    def _edit_user(self) -> None:
        account = self._selected()
        if account is None:
            return
        dialog = _EditUserDialog(account, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        def save() -> None:
            self._services.users.rename_user(account.user_id, dialog.username.text())
            self._services.users.set_email(account.user_id, dialog.email.text())

        self._run(save)

    def _assign_role(self) -> None:
        account = self._selected()
        if account is None:
            return
        dialog = _RoleDialog(account, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._run(lambda: self._services.users.assign_role(account.user_id, dialog.role.role()))

    def _toggle_active(self) -> None:
        account = self._selected()
        if account is None:
            return
        if account.is_active:
            answer = QMessageBox.question(
                self,
                "Deactivate account",
                f"Deactivate {account.username}? The account cannot sign in afterwards.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._run(lambda: self._services.users.deactivate_user(account.user_id))
        else:
            self._run(lambda: self._services.users.activate_user(account.user_id))

    def _reset_password(self) -> None:
        account = self._selected()
        if account is None:
            return
        dialog = _ResetPasswordDialog(account, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        def reset() -> None:
            self._services.passwords.reset_admin(
                account.user_id, dialog.password.text(), dialog.confirmation.text()
            )
            dialog._clear_passwords()

        self._run(reset)


__all__ = [
    "FirstRunDialog",
    "LoginDialog",
    "LockDialog",
    "PasswordChangeDialog",
    "UserManagementDialog",
]
