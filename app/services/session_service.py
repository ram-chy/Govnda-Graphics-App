"""In-memory authenticated session and idle-lock state.

No session state is persisted. Passwords, hashes, tokens, and reset secrets are
never held here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.exceptions import SessionError
from app.domain.auth import RoleKey, SessionIdentity

Clock = Callable[[], str]

DEFAULT_IDLE_TIMEOUT_SECONDS = 15 * 60


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class SessionState:
    """Mutable state of the single authenticated session."""

    identity: SessionIdentity
    role_key: RoleKey
    logged_in_at: str
    last_activity_at: str
    locked: bool = False
    reauthenticated_for: set[str] = field(default_factory=set)


class SessionService:
    """Owns the in-memory session and enforces its lock state."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or _utc_timestamp
        self._session: SessionState | None = None
        self._idle_timeout_seconds = DEFAULT_IDLE_TIMEOUT_SECONDS

    # -- lifecycle ---------------------------------------------------------

    @property
    def idle_timeout_seconds(self) -> int:
        return self._idle_timeout_seconds

    def configure_idle_timeout(self, seconds: int) -> None:
        if seconds <= 0:
            raise SessionError("Idle timeout must be a positive duration.")
        self._idle_timeout_seconds = seconds

    def start(self, identity: SessionIdentity) -> SessionState:
        timestamp = self._clock()
        self._session = SessionState(
            identity=identity,
            role_key=identity.role_key,
            logged_in_at=timestamp,
            last_activity_at=timestamp,
        )
        return self._session

    def end(self) -> SessionState | None:
        ended = self._session
        self._session = None
        return ended

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None

    @property
    def is_locked(self) -> bool:
        return self._session is not None and self._session.locked

    @property
    def identity(self) -> SessionIdentity | None:
        return self._session.identity if self._session is not None else None

    @property
    def role_key(self) -> RoleKey | None:
        return self._session.role_key if self._session is not None else None

    @property
    def actor(self) -> str:
        identity = self.require_identity()
        return f"user:{identity.user_id}:{identity.username}"

    def require_identity(self) -> SessionIdentity:
        """Return the identity for an authorized operation, failing when locked."""

        if self._session is None:
            raise SessionError("No authenticated session is active.")
        if self._session.locked:
            raise SessionError("The session is locked.")
        return self._session.identity

    # -- activity and lock -------------------------------------------------

    def touch(self) -> None:
        if self._session is not None and not self._session.locked:
            self._session.last_activity_at = self._clock()

    def idle_seconds(self) -> float:
        if self._session is None:
            return 0.0
        last = datetime.fromisoformat(self._session.last_activity_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(UTC) - last).total_seconds())

    def should_lock(self) -> bool:
        return (
            self.is_authenticated
            and not self.is_locked
            and self.idle_seconds() >= self.idle_timeout_seconds
        )

    def lock(self) -> bool:
        if self._session is None or self._session.locked:
            return False
        self._session.locked = True
        self._session.reauthenticated_for.clear()
        return True

    def unlock(self) -> bool:
        if self._session is None or not self._session.locked:
            return False
        self._session.locked = False
        self._session.last_activity_at = self._clock()
        return True

    def refresh_role(self, role_key: RoleKey) -> bool:
        if self._session is None:
            return False
        changed = self._session.role_key != role_key
        self._session.role_key = role_key
        return changed

    def refresh_identity_username(self, username: str) -> None:
        """Keep the non-secret identity label in sync after an admin rename."""

        if self._session is not None:
            identity = self._session.identity
            self._session.identity = SessionIdentity(
                user_id=identity.user_id,
                username=username,
                role_key=identity.role_key,
            )

    def invalidate_user(self, user_id: int) -> bool:
        if self._session is not None and self._session.identity.user_id == user_id:
            self._session = None
            return True
        return False

    def clear_reauthentication(self) -> None:
        if self._session is not None:
            self._session.reauthenticated_for.clear()


__all__ = ["DEFAULT_IDLE_TIMEOUT_SECONDS", "SessionService", "SessionState"]
