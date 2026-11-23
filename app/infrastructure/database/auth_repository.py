"""Repositories for local accounts and persistent login throttling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.auth import (
    RoleKey,
    StoredUser,
    UserAccount,
    normalize_email,
    normalize_username,
    role_from_key,
)
from app.infrastructure.database.models.auth import (
    LoginThrottleRecord,
    RoleRecord,
    UserRecord,
)

Clock = Callable[[], str]
FAILED_ATTEMPT_LIMIT = 5
COOLDOWN_SECONDS = 15 * 60


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    """Parse the UTC ISO-8601 strings used throughout the application."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_account(record: UserRecord) -> UserAccount:
    role = role_from_key(record.role_key)
    if role is None:
        raise NotFoundError("The account has an unknown role.")
    return UserAccount(
        user_id=int(record.id),
        username=record.username,
        username_key=record.username_key,
        email=record.email,
        role_key=role,
        is_active=bool(record.is_active),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def to_stored(record: UserRecord) -> StoredUser:
    return StoredUser(account=to_account(record), password_hash=record.password_hash)


class UserAccountRepository:
    """Persistence for local accounts; never returns hashes to presentation code."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def count(self) -> int:
        return len(self._session.scalars(select(UserRecord.id)).all())

    def count_active(self) -> int:
        return len(
            self._session.scalars(select(UserRecord.id).where(UserRecord.is_active == 1)).all()
        )

    def count_active_admins(self) -> int:
        return len(
            self._session.scalars(
                select(UserRecord.id).where(
                    UserRecord.is_active == 1,
                    UserRecord.role_key == RoleKey.OWNER_ADMIN.value,
                )
            ).all()
        )

    def list(self) -> tuple[UserAccount, ...]:
        records = self._session.scalars(select(UserRecord).order_by(UserRecord.id)).all()
        return tuple(to_account(record) for record in records)

    def get(self, user_id: int) -> StoredUser | None:
        record = self._session.get(UserRecord, user_id)
        return to_stored(record) if record is not None else None

    def find_by_username_key(self, username_key: str) -> StoredUser | None:
        record = self._session.scalar(
            select(UserRecord).where(UserRecord.username_key == username_key)
        )
        return to_stored(record) if record is not None else None

    def find_by_username(self, username: str) -> StoredUser | None:
        return self.find_by_username_key(normalize_username(username))

    def add(
        self,
        *,
        username: str,
        username_key: str,
        email: str | None,
        password_hash: str,
        role_key: RoleKey,
    ) -> StoredUser:
        timestamp = self._clock()
        record = UserRecord(
            username=username,
            username_key=username_key,
            email=normalize_email(email),
            password_hash=password_hash,
            is_active=1,
            role_key=role_key.value,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(record)
        self._session.flush()
        return to_stored(record)

    def set_identity(
        self, user_id: int, *, username: str, username_key: str, email: str | None
    ) -> None:
        record = self._require(user_id)
        record.username = username
        record.username_key = username_key
        record.email = normalize_email(email)
        record.updated_at = self._clock()

    def set_active(self, user_id: int, *, is_active: bool) -> None:
        record = self._require(user_id)
        record.is_active = 1 if is_active else 0
        record.updated_at = self._clock()

    def set_role(self, user_id: int, *, role_key: RoleKey) -> None:
        record = self._require(user_id)
        record.role_key = role_key.value
        record.updated_at = self._clock()

    def set_password_hash(self, user_id: int, *, password_hash: str) -> None:
        record = self._require(user_id)
        record.password_hash = password_hash
        record.updated_at = self._clock()

    def _require(self, user_id: int) -> UserRecord:
        record = self._session.get(UserRecord, user_id)
        if record is None:
            raise NotFoundError("The requested user account does not exist.")
        return record


class RoleRepository:
    """Read-only access to the four approved role reference rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_keys(self) -> tuple[RoleKey, ...]:
        records = self._session.scalars(select(RoleRecord).order_by(RoleRecord.key)).all()
        keys = [role_from_key(record.key) for record in records]
        return tuple(key for key in keys if key is not None)


@dataclass(frozen=True, slots=True)
class ThrottleState:
    """Persistent failed-login state for one normalized username."""

    failed_count: int
    first_failed_at: str
    cooldown_until: str | None

    def remaining_seconds(self, now: datetime) -> int:
        if not self.cooldown_until:
            return 0
        remaining = (parse_timestamp(self.cooldown_until) - now).total_seconds()
        return max(0, int(remaining + 0.999))

    def is_cooling_down(self, now: datetime) -> bool:
        return self.remaining_seconds(now) > 0


class LoginThrottleRepository:
    """Persist failed logins so an application restart cannot bypass cooldown."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def get(self, username_key: str) -> ThrottleState | None:
        record = self._session.get(LoginThrottleRecord, username_key)
        if record is None:
            return None
        return ThrottleState(
            failed_count=int(record.failed_count),
            first_failed_at=record.first_failed_at,
            cooldown_until=record.cooldown_until,
        )

    def record_failure(self, username_key: str, *, now: datetime | None = None) -> ThrottleState:
        moment = now or datetime.now(UTC)
        record = self._session.get(LoginThrottleRecord, username_key)
        if record is None:
            record = LoginThrottleRecord(
                username_key=username_key,
                failed_count=0,
                first_failed_at=self._clock(),
                cooldown_until=None,
            )
            self._session.add(record)
        if record.cooldown_until and parse_timestamp(record.cooldown_until) <= moment:
            record.failed_count = 0
            record.first_failed_at = self._clock()
            record.cooldown_until = None
        record.failed_count = int(record.failed_count) + 1
        if record.failed_count >= FAILED_ATTEMPT_LIMIT:
            end = moment.timestamp() + COOLDOWN_SECONDS
            record.cooldown_until = (
                datetime.fromtimestamp(end, UTC).isoformat().replace("+00:00", "Z")
            )
        return ThrottleState(
            failed_count=int(record.failed_count),
            first_failed_at=record.first_failed_at,
            cooldown_until=record.cooldown_until,
        )

    def clear(self, username_key: str) -> None:
        record = self._session.get(LoginThrottleRecord, username_key)
        if record is not None:
            self._session.delete(record)


__all__ = [
    "COOLDOWN_SECONDS",
    "FAILED_ATTEMPT_LIMIT",
    "LoginThrottleRepository",
    "RoleRepository",
    "ThrottleState",
    "UserAccountRepository",
    "parse_timestamp",
    "to_account",
    "to_stored",
]
