"""Authentication and authorization domain values.

Phase 8B implements the owner-approved Phase 8A design. Only permissions marked
``A`` in ``AUTHORIZATION_MATRIX.md`` are granted; proposed (``P``) and open
(``O``) permissions are deliberately absent. This module has no Qt, database,
filesystem, or service dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

# ---------------------------------------------------------------------------
# Roles and permissions
# ---------------------------------------------------------------------------


class RoleKey(StrEnum):
    """The four and only four owner-approved role keys."""

    OWNER_ADMIN = "owner_admin"
    OPERATOR = "operator"
    ACCOUNTANT_REVIEWER = "accountant_reviewer"
    VIEWER = "viewer"


class PermissionKey(StrEnum):
    """Owner-approved permission keys implemented in Phase 8B.

    Keys marked ``P`` or ``O`` in the authorization matrix are intentionally
    omitted so that an unapproved permission cannot be granted by default.
    """

    # Entry-point permission. It is intentionally absent from role grants:
    # login happens before an authenticated role exists.
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    UNLOCK = "auth.unlock"
    PASSWORD_CHANGE_SELF = "auth.password_change_self"

    USER_CREATE = "user.create"
    USER_EDIT_IDENTITY = "user.edit_identity"
    USER_ACTIVATE = "user.activate"
    USER_DEACTIVATE = "user.deactivate"
    USER_RESET_PASSWORD = "user.reset_password"
    USER_ASSIGN_ROLE = "user.assign_role"
    PERMISSION_CHANGE = "permission.change"

    SETTINGS_APPLICATION_UPDATE = "settings.application.update"
    BACKUP_RESTORE = "backup.restore"
    DATABASE_RELOCATE = "database.relocate"

    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"

    PARTY_VIEW = "party.view"
    PARTY_CREATE = "party.create"
    PARTY_EDIT = "party.edit"

    CATALOGUE_VIEW = "catalogue.view"
    CATALOGUE_CREATE = "catalogue.create"
    CATALOGUE_EDIT = "catalogue.edit"


ROLE_DISPLAY_NAMES: dict[RoleKey, str] = {
    RoleKey.OWNER_ADMIN: "Owner/Admin",
    RoleKey.OPERATOR: "Operator",
    RoleKey.ACCOUNTANT_REVIEWER: "Accountant/Reviewer",
    RoleKey.VIEWER: "Viewer",
}

# Owner/Admin has full access to every approved role-grantable operation
# (matrix §4.1), except ``audit.modify`` which is denied to every role and is
# not a grantable key. ``auth.login`` is an unauthenticated entry point, not a
# role grant. Proposed (``P``) and open (``O``) keys are not defined at all.
_ALL_APPROVED_PERMISSIONS = frozenset(
    key for key in PermissionKey if key is not PermissionKey.LOGIN
)

ROLE_PERMISSIONS: dict[RoleKey, frozenset[PermissionKey]] = {
    RoleKey.OWNER_ADMIN: _ALL_APPROVED_PERMISSIONS,
    RoleKey.OPERATOR: frozenset(
        {
            PermissionKey.LOGOUT,
            PermissionKey.UNLOCK,
            PermissionKey.PASSWORD_CHANGE_SELF,
            PermissionKey.PARTY_VIEW,
            PermissionKey.PARTY_CREATE,
            PermissionKey.PARTY_EDIT,
            PermissionKey.CATALOGUE_VIEW,
            PermissionKey.CATALOGUE_CREATE,
            PermissionKey.CATALOGUE_EDIT,
        }
    ),
    RoleKey.ACCOUNTANT_REVIEWER: frozenset(
        {
            PermissionKey.LOGOUT,
            PermissionKey.UNLOCK,
            PermissionKey.PASSWORD_CHANGE_SELF,
            PermissionKey.PARTY_VIEW,
            PermissionKey.CATALOGUE_VIEW,
        }
    ),
    RoleKey.VIEWER: frozenset(
        {
            PermissionKey.LOGOUT,
            PermissionKey.UNLOCK,
            PermissionKey.PASSWORD_CHANGE_SELF,
            PermissionKey.PARTY_VIEW,
            PermissionKey.CATALOGUE_VIEW,
        }
    ),
}

# Immutable public view. Permission sets themselves are frozen.
APPROVED_ROLE_PERMISSIONS = MappingProxyType(ROLE_PERMISSIONS)


def role_from_key(value: str) -> RoleKey | None:
    """Return the role for a stored key, or ``None`` when it is unknown."""

    try:
        return RoleKey(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Identity and credentials
# ---------------------------------------------------------------------------

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 100
MAX_EMAIL_LENGTH = 255
MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True, slots=True)
class PasswordValidation:
    """Result of checking a candidate password against the approved policy."""

    valid: bool
    errors: tuple[str, ...] = ()


def validate_password(password: str, confirmation: str | None = None) -> PasswordValidation:
    """Enforce min 8 characters with upper, lower and digit (``P8A-02``)."""

    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if not any(character.isupper() for character in password):
        errors.append("Password must contain an uppercase letter.")
    if not any(character.islower() for character in password):
        errors.append("Password must contain a lowercase letter.")
    if not any(character.isdigit() for character in password):
        errors.append("Password must contain a digit.")
    if confirmation is not None and password != confirmation:
        errors.append("Password and confirmation do not match.")
    return PasswordValidation(valid=not errors, errors=tuple(errors))


@dataclass(frozen=True, slots=True)
class UsernameValidation:
    """Result of validating a username for local account identity."""

    valid: bool
    normalized: str = ""
    errors: tuple[str, ...] = ()


def normalize_username(username: str) -> str:
    """Case-fold a username for case-insensitive uniqueness (``P8A-01``)."""

    return username.strip().casefold()


def validate_username(username: str) -> UsernameValidation:
    """Validate username length and allowed characters."""

    normalized = normalize_username(username)
    errors: list[str] = []
    if len(normalized) < MIN_USERNAME_LENGTH:
        errors.append(f"Username must be at least {MIN_USERNAME_LENGTH} characters long.")
    if len(normalized) > MAX_USERNAME_LENGTH:
        errors.append(f"Username must be at most {MAX_USERNAME_LENGTH} characters long.")
    if any(character.isspace() for character in username.strip()):
        errors.append("Username must not contain spaces.")
    return UsernameValidation(valid=not errors, normalized=normalized, errors=tuple(errors))


def normalize_email(email: str | None) -> str | None:
    """Trim an optional email; blank input is stored as ``None``."""

    if email is None:
        return None
    value = email.strip()
    return value or None


@dataclass(frozen=True, slots=True)
class UserAccount:
    """Non-secret account view safe for application and presentation layers."""

    user_id: int
    username: str
    username_key: str
    email: str | None
    role_key: RoleKey
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class StoredUser:
    """Internal account view including the password hash.

    Never expose this object, its hash, or its fields through a UI, log, audit
    payload, or application response.
    """

    account: UserAccount
    password_hash: str


@dataclass(frozen=True, slots=True)
class SessionIdentity:
    """Immutable identity snapshot captured when a session is authenticated."""

    user_id: int
    username: str
    role_key: RoleKey


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """Outcome of a username/password authentication attempt."""

    success: bool
    identity: SessionIdentity | None = None
    message: str = ""
    cooldown_remaining_seconds: int = 0


GENERIC_AUTH_FAILURE = "The username or password is incorrect."

# ---------------------------------------------------------------------------
# Actor attribution and audit event names
# ---------------------------------------------------------------------------

USER_ENTITY_TYPE = "user"
SESSION_ENTITY_TYPE = "session"
AUTH_ENTITY_TYPE = "authentication"
ADMIN_ENTITY_TYPE = "administration"


def actor_for_user(user_id: int, username: str) -> str:
    """Build a non-secret actor label derived from the authenticated user."""

    return f"user:{user_id}:{username}"


class AuthEventType:
    """Append-only audit event names for authentication and administration."""

    OWNER_ACCOUNT_CREATED = "auth.owner_account_created"
    LOGIN_SUCCEEDED = "auth.login_succeeded"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    LOCK = "auth.lock"
    UNLOCK = "auth.unlock"
    PASSWORD_CHANGED = "auth.password_changed"
    PASSWORD_RESET_ADMIN = "auth.password_reset_admin"
    USER_CREATED = "auth.user_created"
    USER_UPDATED = "auth.user_updated"
    USER_ACTIVATED = "auth.user_activated"
    USER_DEACTIVATED = "auth.user_deactivated"
    ROLE_ASSIGNED = "auth.role_assigned"
    PERMISSION_CHANGED = "auth.permission_changed"
    ACCESS_DENIED = "auth.access_denied"


class AdminEventType:
    """Administrative audit event names required by the authorization matrix."""

    SETTINGS_CHANGED = "admin.settings_changed"
    BACKUP_RESTORED = "backup.restored"
    DATABASE_RELOCATED = "admin.database_relocated"
    AUDIT_EXPORTED = "audit.exported"


__all__ = [
    "ADMIN_ENTITY_TYPE",
    "APPROVED_ROLE_PERMISSIONS",
    "AUTH_ENTITY_TYPE",
    "AuthEventType",
    "AdminEventType",
    "AuthenticationResult",
    "GENERIC_AUTH_FAILURE",
    "MIN_PASSWORD_LENGTH",
    "PermissionKey",
    "PasswordValidation",
    "RoleKey",
    "ROLE_DISPLAY_NAMES",
    "ROLE_PERMISSIONS",
    "SESSION_ENTITY_TYPE",
    "SessionIdentity",
    "StoredUser",
    "USER_ENTITY_TYPE",
    "UserAccount",
    "UsernameValidation",
    "actor_for_user",
    "normalize_email",
    "normalize_username",
    "role_from_key",
    "validate_password",
    "validate_username",
]
