"""Owner/Admin user administration and password management services."""

from __future__ import annotations

from app.core.exceptions import ConflictError, DomainRuleError, ValidationError
from app.domain.auth import (
    USER_ENTITY_TYPE,
    AuthEventType,
    PermissionKey,
    RoleKey,
    UserAccount,
    normalize_email,
    validate_password,
    validate_username,
)
from app.infrastructure.database.auth_repository import UserAccountRepository
from app.infrastructure.security.password_hasher import PasswordHasher
from app.services.auth_support import (
    AuthAuditService,
    DatabaseSource,
    actor_payload,
    database_provider,
)
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService

ADMIN_ROLE = RoleKey.OWNER_ADMIN


class UserAccountService:
    """Local account lifecycle with last-active-admin safeguards."""

    def __init__(
        self,
        database: DatabaseSource,
        authorization: AuthorizationService,
        session: SessionService,
        audit: AuthAuditService,
        hasher: PasswordHasher,
    ) -> None:
        self._database = database_provider(database)
        self._authorization = authorization
        self._session = session
        self._audit = audit
        self._hasher = hasher

    def list_users(self) -> tuple[UserAccount, ...]:
        self._authorization.require(PermissionKey.USER_EDIT_IDENTITY)
        with self._database().unit_of_work() as work:
            return UserAccountRepository(work.session).list()

    def create_user(
        self,
        username: str,
        password: str,
        role_key: RoleKey,
        *,
        email: str | None = None,
        confirmation: str | None = None,
    ) -> UserAccount:
        self._authorization.require(PermissionKey.USER_CREATE)
        name_check = validate_username(username)
        password_check = validate_password(password, confirmation)
        if not name_check.valid or not password_check.valid:
            raise ValidationError(
                "User details are invalid.",
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
        password_hash = self._hasher.hash(password)
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            if users.find_by_username_key(name_check.normalized) is not None:
                raise ConflictError(
                    "Username already exists.", user_message="That username is already in use."
                )
            stored = users.add(
                username=username.strip(),
                username_key=name_check.normalized,
                email=normalize_email(email),
                password_hash=password_hash,
                role_key=role_key,
            )
            work.commit()
            account = stored.account
        self._audit.record(
            event_type=AuthEventType.USER_CREATED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(account.user_id),
            actor=self._session.actor,
            payload={"username": account.username, "role": account.role_key.value},
        )
        self._audit.record(
            event_type=AuthEventType.ROLE_ASSIGNED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(account.user_id),
            actor=self._session.actor,
            payload={"role": account.role_key.value},
        )
        return account

    def rename_user(self, user_id: int, username: str) -> UserAccount:
        self._authorization.require(PermissionKey.USER_EDIT_IDENTITY)
        name_check = validate_username(username)
        if not name_check.valid:
            raise ValidationError(
                "Username is invalid.",
                field_errors={"username": name_check.errors[0]},
                user_message=name_check.errors[0],
            )
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            existing = users.find_by_username_key(name_check.normalized)
            if existing is not None and existing.account.user_id != user_id:
                raise ConflictError(
                    "Username already exists.", user_message="That username is already in use."
                )
            target = users.get(user_id)
            if target is None:
                raise ValidationError("User not found.", user_message="The user does not exist.")
            users.set_identity(
                user_id,
                username=username.strip(),
                username_key=name_check.normalized,
                email=target.account.email,
            )
            work.commit()
            updated = users.get(user_id)
            assert updated is not None
        self._audit.record(
            event_type=AuthEventType.USER_UPDATED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(user_id),
            actor=self._session.actor,
            payload={"field": "username", "username": updated.account.username},
        )
        if self._session.identity is not None and self._session.identity.user_id == user_id:
            self._session.refresh_identity_username(updated.account.username)
        return updated.account

    def set_email(self, user_id: int, email: str | None) -> UserAccount:
        self._authorization.require(PermissionKey.USER_EDIT_IDENTITY)
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            target = users.get(user_id)
            if target is None:
                raise ValidationError("User not found.", user_message="The user does not exist.")
            users.set_identity(
                user_id,
                username=target.account.username,
                username_key=target.account.username_key,
                email=email,
            )
            work.commit()
            updated = users.get(user_id)
            assert updated is not None
        self._audit.record(
            event_type=AuthEventType.USER_UPDATED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(user_id),
            actor=self._session.actor,
            payload={"field": "email", "has_email": bool(normalize_email(email))},
        )
        return updated.account

    def deactivate_user(self, user_id: int) -> UserAccount:
        self._authorization.require(PermissionKey.USER_DEACTIVATE)
        actor = self._session.actor
        payload = actor_payload(self._session)
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            target = users.get(user_id)
            if target is None:
                raise ValidationError("User not found.", user_message="The user does not exist.")
            if (
                target.account.role_key == ADMIN_ROLE
                and target.account.is_active
                and users.count_active_admins() <= 1
            ):
                raise DomainRuleError(
                    "The last active Owner/Admin cannot be deactivated.",
                    user_message="At least one active Owner/Admin must remain.",
                )
            users.set_active(user_id, is_active=False)
            work.commit()
            updated = users.get(user_id)
            assert updated is not None
        self._session.invalidate_user(user_id)
        self._audit.record(
            event_type=AuthEventType.USER_DEACTIVATED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(user_id),
            actor=actor,
            payload=payload,
        )
        return updated.account

    def activate_user(self, user_id: int) -> UserAccount:
        self._authorization.require(PermissionKey.USER_ACTIVATE)
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            target = users.get(user_id)
            if target is None:
                raise ValidationError("User not found.", user_message="The user does not exist.")
            users.set_active(user_id, is_active=True)
            work.commit()
            updated = users.get(user_id)
            assert updated is not None
        self._audit.record(
            event_type=AuthEventType.USER_ACTIVATED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(user_id),
            actor=self._session.actor,
            payload={"username": updated.account.username},
        )
        return updated.account

    def assign_role(self, user_id: int, role_key: RoleKey) -> UserAccount:
        self._authorization.require(PermissionKey.USER_ASSIGN_ROLE)
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            target = users.get(user_id)
            if target is None:
                raise ValidationError("User not found.", user_message="The user does not exist.")
            if (
                target.account.role_key == ADMIN_ROLE
                and target.account.is_active
                and role_key != ADMIN_ROLE
                and users.count_active_admins() <= 1
            ):
                raise DomainRuleError(
                    "The last active Owner/Admin cannot be downgraded.",
                    user_message="At least one active Owner/Admin must remain.",
                )
            users.set_role(user_id, role_key=role_key)
            work.commit()
            updated = users.get(user_id)
            assert updated is not None
        if self._session.identity is not None and self._session.identity.user_id == user_id:
            self._session.refresh_role(role_key)
        self._audit.record(
            event_type=AuthEventType.ROLE_ASSIGNED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(user_id),
            actor=self._session.actor,
            payload={"role": role_key.value},
        )
        return updated.account


class PasswordService:
    """Self-service password change and audited administrative reset."""

    def __init__(
        self,
        database: DatabaseSource,
        authorization: AuthorizationService,
        session: SessionService,
        audit: AuthAuditService,
        hasher: PasswordHasher,
    ) -> None:
        self._database = database_provider(database)
        self._authorization = authorization
        self._session = session
        self._audit = audit
        self._hasher = hasher

    def change_self(self, current: str, new: str, confirmation: str) -> None:
        self._authorization.require(PermissionKey.PASSWORD_CHANGE_SELF)
        identity = self._session.require_identity()
        check = validate_password(new, confirmation)
        if not check.valid:
            raise ValidationError(
                "New password is invalid.",
                field_errors={
                    f"password_{index}": message for index, message in enumerate(check.errors)
                },
                user_message=(
                    "Use 8+ characters with an uppercase letter, a lowercase letter and a digit."
                ),
            )
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            stored = users.get(identity.user_id)
            if stored is None or not self._hasher.verify(stored.password_hash, current):
                raise ValidationError(
                    "Current password is incorrect.",
                    field_errors={"current_password": "The current password is incorrect."},
                    user_message="The current password is incorrect.",
                )
            users.set_password_hash(identity.user_id, password_hash=self._hasher.hash(new))
            work.commit()
        self._session.clear_reauthentication()
        self._audit.record(
            event_type=AuthEventType.PASSWORD_CHANGED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(identity.user_id),
            actor=self._session.actor,
            payload=actor_payload(self._session),
        )

    def reset_admin(self, user_id: int, new: str, confirmation: str) -> None:
        self._authorization.require(PermissionKey.USER_RESET_PASSWORD)
        actor = self._session.actor
        payload = actor_payload(self._session)
        check = validate_password(new, confirmation)
        if not check.valid:
            raise ValidationError(
                "New password is invalid.",
                field_errors={
                    f"password_{index}": message for index, message in enumerate(check.errors)
                },
                user_message=(
                    "Use 8+ characters with an uppercase letter, a lowercase letter and a digit."
                ),
            )
        with self._database().unit_of_work() as work:
            users = UserAccountRepository(work.session)
            if users.get(user_id) is None:
                raise ValidationError("User not found.", user_message="The user does not exist.")
            users.set_password_hash(user_id, password_hash=self._hasher.hash(new))
            work.commit()
        self._session.invalidate_user(user_id)
        self._audit.record(
            event_type=AuthEventType.PASSWORD_RESET_ADMIN,
            entity_type=USER_ENTITY_TYPE,
            entity_id=str(user_id),
            actor=actor,
            payload=payload,
        )


__all__ = ["PasswordService", "UserAccountService"]
