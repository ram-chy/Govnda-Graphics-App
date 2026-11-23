"""Centralized permission checks enforced at the application-service boundary."""

from __future__ import annotations

from app.core.exceptions import AuthorizationError, SessionError
from app.domain.auth import APPROVED_ROLE_PERMISSIONS, PermissionKey, RoleKey
from app.infrastructure.database.auth_repository import UserAccountRepository
from app.services.auth_support import DatabaseSource, database_provider
from app.services.session_service import SessionService


class AuthorizationService:
    """Single source of truth for runtime authorization decisions.

    The role snapshot is refreshed from the database at each check so role and
    status changes take effect on the next authorization check (``P8A-07``).
    UI visibility is advisory only; callers must use :meth:`require`.
    """

    def __init__(self, session: SessionService, database: DatabaseSource | None = None) -> None:
        self._session = session
        self._database = database_provider(database) if database is not None else None

    def has_permission(self, permission: PermissionKey | str) -> bool:
        try:
            identity = self._session.require_identity()
        except SessionError:
            return False
        role: RoleKey = self._session.role_key or identity.role_key
        if self._database is not None:
            with self._database().unit_of_work() as work:
                stored = UserAccountRepository(work.session).get(identity.user_id)
            if stored is None or not stored.account.is_active:
                self._session.end()
                return False
            if stored.account.role_key != role:
                self._session.refresh_role(stored.account.role_key)
                role = stored.account.role_key
        try:
            key = permission if isinstance(permission, PermissionKey) else PermissionKey(permission)
        except ValueError:
            return False
        granted: frozenset[PermissionKey] = APPROVED_ROLE_PERMISSIONS.get(role, frozenset())
        return key in granted

    def require(self, permission: PermissionKey | str) -> None:
        """Raise a safe authorization error when the operation is not allowed."""

        if self.has_permission(permission):
            return
        key = permission.value if isinstance(permission, PermissionKey) else permission
        raise AuthorizationError(
            f"Permission denied: {key}",
            user_message="You do not have permission to perform this operation.",
            permission=key,
        )

    def permissions_for_session(self) -> frozenset[PermissionKey]:
        """Return the permissions for the current session, for UI filtering only."""

        try:
            self._session.require_identity()
        except SessionError:
            return frozenset()
        role = self._session.role_key
        if role is None:
            return frozenset()
        return APPROVED_ROLE_PERMISSIONS.get(role, frozenset())


__all__ = ["AuthorizationService"]
