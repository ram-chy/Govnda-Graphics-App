"""Service-layer gate and audit recording for sensitive operations."""

from __future__ import annotations

from app.domain.auth import PermissionKey
from app.services.auth_support import AuthAuditService
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService


class SensitiveOperationService:
    """Central gate for operations that require an approved permission.

    Views and view models call :meth:`require` before starting work, and
    :meth:`record` after a successful operation. Authorization therefore lives
    in the application layer and cannot be replaced by hiding a UI control.
    """

    def __init__(
        self,
        authorization: AuthorizationService,
        session: SessionService,
        audit: AuthAuditService,
    ) -> None:
        self._authorization = authorization
        self._session = session
        self._audit = audit

    def require(self, permission: PermissionKey) -> None:
        self._authorization.require(permission)

    def allows(self, permission: PermissionKey) -> bool:
        """Return an advisory result for UI enablement only."""

        return self._authorization.has_permission(permission)

    def record(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        self._audit.record(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=self._session.actor,
            payload=payload,
        )


__all__ = ["SensitiveOperationService"]
