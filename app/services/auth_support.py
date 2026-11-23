"""Actor attribution and authentication audit writing."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.audit import UNAUTHENTICATED_ACTOR, AuditEvent
from app.domain.auth import actor_for_user
from app.infrastructure.database.auth_repository import UserAccountRepository
from app.infrastructure.database.business_profile_repository import AuditEventRepository
from app.infrastructure.database.engine import Database
from app.infrastructure.database.models import AuditEventRecord
from app.services.database_runtime import DatabaseRuntime

Clock = Callable[[], str]
DatabaseSource = Database | DatabaseRuntime
DatabaseProvider = Callable[[], Database]


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def database_provider(source: DatabaseSource) -> DatabaseProvider:
    """Return a callable that always resolves the live database.

    Restore and relocation replace the open :class:`Database`; services that
    cache one instance would write audit rows to the replaced file. Resolving
    through :class:`DatabaseRuntime` on every call avoids that stale reference.
    """

    if isinstance(source, DatabaseRuntime):
        return source.require
    if isinstance(source, Database):
        return lambda: source
    raise TypeError("database source must be a Database or DatabaseRuntime")  # pragma: no cover


def compact_json(values: dict[str, object]) -> str:
    """Serialize an audit payload without secrets or pretty formatting."""

    return json.dumps(values, separators=(",", ":"), sort_keys=True)


class ActorProvider:
    """Supplies the non-secret actor label for the current in-memory session."""

    def __init__(self, session: object) -> None:
        self._session = session

    def current(self) -> str:
        identity = getattr(self._session, "identity", None)
        if identity is None:
            return UNAUTHENTICATED_ACTOR
        return actor_for_user(identity.user_id, identity.username)

    def unauthenticated(self) -> str:
        return UNAUTHENTICATED_ACTOR


class AuthAuditService:
    """Append-only audit writing for authentication and administration events."""

    def __init__(self, database: DatabaseSource, *, clock: Clock | None = None) -> None:
        self._database = database_provider(database)
        self._clock = clock or _utc_timestamp

    def record(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        payload: dict[str, object] | None = None,
    ) -> AuditEventRecord:
        event = AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            created_at=self._clock(),
            payload=compact_json(payload or {}),
        )
        with self._database().unit_of_work() as work:
            record = AuditEventRepository(work.session, clock=self._clock).add(event)
            work.commit()
            return record


def actor_payload(session: object) -> dict[str, object]:
    """Build a non-secret role snapshot for an authenticated audit event."""

    identity = getattr(session, "identity", None)
    if identity is None:
        return {}
    role = getattr(session, "role_key", None)
    role_value = role.value if hasattr(role, "value") else identity.role_key.value
    return {
        "user_id": identity.user_id,
        "username": identity.username,
        "role": role_value,
    }


def account_exists(database: DatabaseSource) -> bool:
    """Return whether any local account exists (used by the first-run gate)."""

    with database_provider(database)().unit_of_work() as work:
        return UserAccountRepository(work.session).count() > 0


__all__ = [
    "ActorProvider",
    "AuthAuditService",
    "DatabaseProvider",
    "DatabaseSource",
    "account_exists",
    "actor_payload",
    "compact_json",
    "database_provider",
]
