"""Authentication workflows: first-run owner, login, unlock, and logout."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ValidationError
from app.domain.audit import UNAUTHENTICATED_ACTOR
from app.domain.auth import (
    AUTH_ENTITY_TYPE,
    GENERIC_AUTH_FAILURE,
    SESSION_ENTITY_TYPE,
    USER_ENTITY_TYPE,
    AuthenticationResult,
    AuthEventType,
    SessionIdentity,
    UserAccount,
    normalize_email,
    normalize_username,
    role_from_key,
    validate_password,
    validate_username,
)
from app.infrastructure.database.auth_repository import (
    COOLDOWN_SECONDS,
    FAILED_ATTEMPT_LIMIT,
    LoginThrottleRepository,
    UserAccountRepository,
)
from app.infrastructure.security.password_hasher import PasswordHasher
from app.services.auth_support import (
    AuthAuditService,
    DatabaseSource,
    actor_payload,
    database_provider,
)
from app.services.session_service import SessionService

NowFn = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AuthenticationService:
    """Implements only owner-approved authentication behavior."""

    def __init__(
        self,
        database: DatabaseSource,
        hasher: PasswordHasher,
        session: SessionService,
        audit: AuthAuditService,
        *,
        now: NowFn | None = None,
    ) -> None:
        self._database = database_provider(database)
        self._hasher = hasher
        self._session = session
        self._audit = audit
        self._now = now or _utc_now

    # -- first run ---------------------------------------------------------

    def has_accounts(self) -> bool:
        with self._database().unit_of_work() as work:
            return UserAccountRepository(work.session).count() > 0

    def create_first_run_owner(
        self,
        username: str,
        password: str,
        *,
        email: str | None = None,
        confirmation: str | None = None,
    ) -> UserAccount:
        """Create the initial Owner/Admin in a single transaction.

        The local single-instance guard serializes concurrent launches, and the
        unique username key prevents a second initial account from being added.
        """

        name_check = validate_username(username)
        password_check = validate_password(password, confirmation)
        if not name_check.valid or not password_check.valid:
            raise ValidationError(
                "First-run owner details are invalid.",
                field_errors={
                    **({"username": name_check.errors[0]} if name_check.errors else {}),
                    **{
                        f"password_{index}": message
                        for index, message in enumerate(password_check.errors)
                    },
                },
                user_message=(
                    "Enter a valid username and a password with 8+ characters, "
                    "upper, lower and digit."
                ),
            )

        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            if users.count() > 0:
                raise ConflictError(
                    "An account already exists; first-run setup cannot be repeated.",
                    user_message="First-run setup has already been completed.",
                )
            password_hash = self._hasher.hash(password)
            stored = users.add(
                username=username.strip(),
                username_key=name_check.normalized,
                email=normalize_email(email),
                password_hash=password_hash,
                role_key=role_from_key("owner_admin"),  # type: ignore[arg-type]
            )
            work.commit()
            account = stored.account

        self._audit.record(
            event_type=AuthEventType.OWNER_ACCOUNT_CREATED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(account.user_id),
            actor=UNAUTHENTICATED_ACTOR,
            payload={"username": account.username, "role": account.role_key.value},
        )
        return account

    # -- login -------------------------------------------------------------

    def authenticate(
        self, username: str, password: str, *, purpose: str = "login"
    ) -> AuthenticationResult:
        """Verify credentials and return a generic result without account disclosure."""

        username_key = normalize_username(username)
        now = self._now()
        with self._database().unit_of_work() as work:
            throttles = LoginThrottleRepository(work.session)
            state = throttles.get(username_key)
            if state is not None and state.is_cooling_down(now):
                self._record_login_failed(username_key, purpose, "cooldown")
                return AuthenticationResult(
                    success=False,
                    message="Too many failed attempts. Try again in "
                    f"{state.remaining_seconds(now)} seconds.",
                    cooldown_remaining_seconds=state.remaining_seconds(now),
                )
            stored = UserAccountRepository(work.session).find_by_username_key(username_key)
            valid = (
                stored is not None
                and stored.account.is_active
                and self._hasher.verify(stored.password_hash, password)
            )
            if not valid:
                throttles.record_failure(username_key, now=now)
                work.commit()
                self._record_login_failed(username_key, purpose, "invalid_credentials")
                return AuthenticationResult(
                    success=False,
                    message=GENERIC_AUTH_FAILURE,
                )
            assert stored is not None
            if self._hasher.needs_rehash(stored.password_hash):
                UserAccountRepository(work.session).set_password_hash(
                    stored.account.user_id, password_hash=self._hasher.hash(password)
                )
            throttles.clear(username_key)
            work.commit()
            identity = SessionIdentity(
                user_id=stored.account.user_id,
                username=stored.account.username,
                role_key=stored.account.role_key,
            )

        actor = f"user:{identity.user_id}:{identity.username}"
        if purpose == "login":
            self._session.start(identity)
            self._audit.record(
                event_type=AuthEventType.LOGIN_SUCCEEDED,
                entity_type=SESSION_ENTITY_TYPE,
                entity_id=str(identity.user_id),
                actor=actor,
                payload=actor_payload(self._session),
            )
        return AuthenticationResult(success=True, identity=identity)

    def unlock(self, password: str) -> AuthenticationResult:
        """Verify the locked-in user's password and resume the same session."""

        identity = self._session.identity
        if identity is None:
            return AuthenticationResult(success=False, message=GENERIC_AUTH_FAILURE)
        result = self.authenticate(identity.username, password, purpose="unlock")
        if result.success:
            self._session.unlock()
            self._audit.record(
                event_type=AuthEventType.UNLOCK,
                entity_type=SESSION_ENTITY_TYPE,
                entity_id=str(identity.user_id),
                actor=f"user:{identity.user_id}:{identity.username}",
                payload=actor_payload(self._session),
            )
        return result

    def logout(self) -> None:
        ended = self._session.end()
        if ended is None:
            return
        identity = ended.identity
        self._audit.record(
            event_type=AuthEventType.LOGOUT,
            entity_type=SESSION_ENTITY_TYPE,
            entity_id=str(identity.user_id),
            actor=f"user:{identity.user_id}:{identity.username}",
            payload={"role": identity.role_key.value},
        )

    def _record_login_failed(self, username_key: str, purpose: str, reason: str) -> None:
        self._audit.record(
            event_type=AuthEventType.LOGIN_FAILED,
            entity_type=AUTH_ENTITY_TYPE,
            entity_id=username_key[:100],
            actor=UNAUTHENTICATED_ACTOR,
            payload={"purpose": purpose, "reason": reason},
        )


__all__ = ["COOLDOWN_SECONDS", "FAILED_ATTEMPT_LIMIT", "AuthenticationService"]
