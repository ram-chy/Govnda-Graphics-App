"""Composition of authentication and authorization services."""

from __future__ import annotations

from dataclasses import dataclass

from app.core import constants
from app.infrastructure.security.password_hasher import PasswordHasher
from app.services.auth_support import AuthAuditService, DatabaseSource
from app.services.authentication_service import AuthenticationService
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService
from app.services.user_account_service import PasswordService, UserAccountService


@dataclass(slots=True)
class AuthServices:
    """All authentication services sharing one in-memory session."""

    session: SessionService
    hasher: PasswordHasher
    audit: AuthAuditService
    authorization: AuthorizationService
    authentication: AuthenticationService
    users: UserAccountService
    passwords: PasswordService

    @classmethod
    def create(
        cls,
        database: DatabaseSource,
        *,
        idle_timeout_seconds: int = constants.DEFAULT_IDLE_TIMEOUT_SECONDS,
        hasher: PasswordHasher | None = None,
    ) -> AuthServices:
        """Build the graph with the approved idle timeout applied."""

        session = SessionService()
        session.configure_idle_timeout(idle_timeout_seconds)
        password_hasher = hasher or PasswordHasher()
        audit = AuthAuditService(database)
        authorization = AuthorizationService(session, database)
        authentication = AuthenticationService(database, password_hasher, session, audit)
        users = UserAccountService(database, authorization, session, audit, password_hasher)
        passwords = PasswordService(database, authorization, session, audit, password_hasher)
        return cls(
            session=session,
            hasher=password_hasher,
            audit=audit,
            authorization=authorization,
            authentication=authentication,
            users=users,
            passwords=passwords,
        )

    def end_session(self) -> None:
        """Discard the in-memory session without writing a logout event."""

        self.session.end()


__all__ = ["AuthServices"]
