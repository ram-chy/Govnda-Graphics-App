"""Phase 8B authentication, authorization, session, and audit tests.

All tests use isolated temporary databases. No test touches the owner's configured
business database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainRuleError,
    SessionError,
    ValidationError,
)
from app.domain.audit import UNAUTHENTICATED_ACTOR
from app.domain.auth import (
    GENERIC_AUTH_FAILURE,
    AuthEventType,
    PermissionKey,
    RoleKey,
    validate_password,
    validate_username,
)
from app.infrastructure.database.auth_repository import (
    COOLDOWN_SECONDS,
    FAILED_ATTEMPT_LIMIT,
    UserAccountRepository,
)
from app.infrastructure.security.password_hasher import (
    ARGON2_MEMORY_COST_KIB,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
    SALT_LENGTH,
    SCRYPT_DKLEN,
    SCRYPT_MAXMEM,
    SCRYPT_N,
    SCRYPT_P,
    SCRYPT_R,
    PasswordHasher,
)
from app.services.auth_services import AuthServices
from app.services.session_service import DEFAULT_IDLE_TIMEOUT_SECONDS, SessionService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(initialized_database, *, now=None) -> AuthServices:
    auth = AuthServices.create(initialized_database)
    if now is not None:
        # Replace clock-sensitive services for deterministic tests.
        from app.services.auth_support import AuthAuditService
        from app.services.authentication_service import AuthenticationService
        from app.services.user_account_service import PasswordService, UserAccountService

        audit = AuthAuditService(initialized_database)
        auth.audit = audit
        auth.authentication = AuthenticationService(
            initialized_database, auth.hasher, auth.session, audit, now=now
        )
        auth.users = UserAccountService(
            initialized_database, auth.authorization, auth.session, audit, auth.hasher
        )
        auth.passwords = PasswordService(
            initialized_database, auth.authorization, auth.session, audit, auth.hasher
        )
    return auth


def _owner(auth: AuthServices, username: str = "owner", password: str = "Owner123!"):
    return auth.authentication.create_first_run_owner(username, password, confirmation=password)


def _login_owner(auth: AuthServices, username: str = "owner", password: str = "Owner123!"):
    result = auth.authentication.authenticate(username, password)
    assert result.success, result.message
    return result


def _audit_events(initialized_database):
    from app.infrastructure.database.business_profile_repository import AuditEventRepository

    with initialized_database.unit_of_work() as work:
        return AuditEventRepository(work.session).list()


# ---------------------------------------------------------------------------
# Password policy and hashing
# ---------------------------------------------------------------------------


class TestPasswordPolicy:
    def test_minimum_length(self):
        result = validate_password("Aa1shor")  # 7 chars
        assert not result.valid

    def test_requires_upper_lower_digit(self):
        assert not validate_password("alllower1").valid
        assert not validate_password("ALLUPPER1").valid
        assert not validate_password("NoDigitsHere").valid
        assert validate_password("GoodPass1").valid

    def test_confirmation_required_when_provided(self):
        result = validate_password("GoodPass1", "Different1")
        assert not result.valid
        assert any("match" in e.lower() for e in result.errors)

    def test_no_unapproved_complexity_rules(self):
        # Symbols not required; exactly 8 chars is enough.
        assert validate_password("Abcdefg1").valid


class TestPasswordHasher:
    def test_hash_and_verify(self):
        hasher = PasswordHasher(prefer="scrypt")
        stored = hasher.hash("GoodPass1")
        assert hasher.verify(stored, "GoodPass1")
        assert not hasher.verify(stored, "BadPass1")

    def test_unique_salt(self):
        hasher = PasswordHasher(prefer="scrypt")
        a = hasher.hash("GoodPass1")
        b = hasher.hash("GoodPass1")
        assert a != b

    def test_self_describing_scrypt_format(self):
        hasher = PasswordHasher(prefer="scrypt")
        stored = hasher.hash("GoodPass1")
        assert stored.startswith("scrypt$")
        assert f"N={SCRYPT_N}" in stored
        assert f"r={SCRYPT_R}" in stored
        assert f"p={SCRYPT_P}" in stored
        assert f"dklen={SCRYPT_DKLEN}" in stored

    def test_approved_parameters(self):
        assert ARGON2_TIME_COST == 3
        assert ARGON2_MEMORY_COST_KIB == 65536
        assert ARGON2_PARALLELISM == 1
        assert SALT_LENGTH == 16
        assert SCRYPT_N == 2**17
        assert SCRYPT_R == 8
        assert SCRYPT_P == 1
        assert SCRYPT_DKLEN == 32
        assert SCRYPT_MAXMEM > 128 * 1024 * 1024

    def test_needs_rehash_for_wrong_params(self):
        hasher = PasswordHasher(prefer="scrypt")
        assert hasher.needs_rehash("")
        assert hasher.needs_rehash("scrypt$N=16384,r=8,p=1,dklen=32$aa$bb$")

    def test_verify_rejects_malformed_hash(self):
        hasher = PasswordHasher(prefer="scrypt")
        assert not hasher.verify("garbage", "GoodPass1")
        assert not hasher.verify("", "GoodPass1")

    def test_no_plaintext_persistence(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth, password="Secret123!")
        with initialized_database.unit_of_work() as work:
            stored = UserAccountRepository(work.session).find_by_username("owner")
        assert stored is not None
        assert "Secret123!" not in stored.password_hash
        assert stored.password_hash != "Secret123!"


# ---------------------------------------------------------------------------
# Username and first-run
# ---------------------------------------------------------------------------


class TestFirstRunAndIdentity:
    def test_first_run_creates_owner_admin(self, initialized_database):
        auth = _auth(initialized_database)
        account = _owner(auth)
        assert account.role_key == RoleKey.OWNER_ADMIN
        assert account.is_active

    def test_first_run_requires_confirmation(self, initialized_database):
        auth = _auth(initialized_database)
        with pytest.raises(ValidationError):
            auth.authentication.create_first_run_owner(
                "owner", "Owner123!", confirmation="Wrong123!"
            )

    def test_duplicate_first_run_rejected(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        with pytest.raises(ConflictError):
            auth.authentication.create_first_run_owner(
                "other", "Owner123!", confirmation="Owner123!"
            )

    def test_case_insensitive_username_uniqueness(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth, username="Owner")
        _login_owner(auth, username="Owner")
        with pytest.raises(ConflictError):
            auth.users.create_user("owner", "Other123!", RoleKey.OPERATOR, confirmation="Other123!")

    def test_username_validation(self):
        assert validate_username("ab").valid is False  # too short
        assert validate_username("abc").valid is True
        assert validate_username("has space").valid is False


# ---------------------------------------------------------------------------
# Login and throttling
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_login_success(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        result = auth.authentication.authenticate("owner", "Owner123!")
        assert result.success
        assert result.identity is not None
        assert auth.session.is_authenticated

    def test_wrong_password_generic_failure(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        result = auth.authentication.authenticate("owner", "wrong")
        assert not result.success
        assert result.message == GENERIC_AUTH_FAILURE

    def test_unknown_user_generic_failure(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        result = auth.authentication.authenticate("nobody", "wrong")
        assert not result.success
        assert result.message == GENERIC_AUTH_FAILURE

    def test_deactivated_account_rejected(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        # find op id
        with initialized_database.unit_of_work() as work:
            op = UserAccountRepository(work.session).find_by_username("oper")
        assert op is not None
        auth.users.deactivate_user(op.account.user_id)
        auth.authentication.logout()
        result = auth.authentication.authenticate("oper", "Operator1!")
        assert not result.success
        assert result.message == GENERIC_AUTH_FAILURE

    def test_failed_login_cooldown(self, initialized_database):
        t = datetime(2026, 1, 1, tzinfo=UTC)

        def clock():
            return t

        auth = _auth(initialized_database, now=clock)
        _owner(auth)
        for _ in range(FAILED_ATTEMPT_LIMIT):
            r = auth.authentication.authenticate("owner", "badpass")
            assert not r.success
        blocked = auth.authentication.authenticate("owner", "Owner123!")
        assert not blocked.success
        assert "Too many failed attempts" in blocked.message
        assert blocked.cooldown_remaining_seconds > 0

    def test_cooldown_expires(self, initialized_database):
        times = [datetime(2026, 1, 1, tzinfo=UTC)]

        def now():
            return times[0]

        auth = _auth(initialized_database, now=now)
        _owner(auth)
        for _ in range(FAILED_ATTEMPT_LIMIT):
            auth.authentication.authenticate("owner", "badpass")
        times[0] = times[0] + timedelta(seconds=COOLDOWN_SECONDS + 1)
        result = auth.authentication.authenticate("owner", "Owner123!")
        assert result.success

    def test_cooldown_persists_across_service_instances(self, initialized_database):
        times = [datetime(2026, 1, 1, tzinfo=UTC)]

        def now():
            return times[0]

        auth1 = _auth(initialized_database, now=now)
        _owner(auth1)
        for _ in range(FAILED_ATTEMPT_LIMIT):
            auth1.authentication.authenticate("owner", "badpass")
        # New service instance, same DB - simulates restart
        auth2 = _auth(initialized_database, now=now)
        blocked = auth2.authentication.authenticate("owner", "Owner123!")
        assert not blocked.success
        assert "Too many failed attempts" in blocked.message

    def test_throttle_does_not_leak_account_existence(self, initialized_database):
        times = [datetime(2026, 1, 1, tzinfo=UTC)]

        def now():
            return times[0]

        auth = _auth(initialized_database, now=now)
        _owner(auth)
        for _ in range(FAILED_ATTEMPT_LIMIT):
            auth.authentication.authenticate("ghost", "badpass")
        # unknown username also gets cooldown response - no existence leak
        blocked = auth.authentication.authenticate("ghost", "badpass")
        assert not blocked.success
        assert "Too many failed attempts" in blocked.message


# ---------------------------------------------------------------------------
# Password change / reset
# ---------------------------------------------------------------------------


class TestPasswordManagement:
    def test_self_password_change(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.passwords.change_self("Owner123!", "NewPass1!", "NewPass1!")
        auth.authentication.logout()
        assert not auth.authentication.authenticate("owner", "Owner123!").success
        assert auth.authentication.authenticate("owner", "NewPass1!").success

    def test_self_password_change_requires_current(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        with pytest.raises(ValidationError):
            auth.passwords.change_self("wrong", "NewPass1!", "NewPass1!")

    def test_admin_reset(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        with initialized_database.unit_of_work() as work:
            op = UserAccountRepository(work.session).find_by_username("oper")
        auth.passwords.reset_admin(op.account.user_id, "Reset123!", "Reset123!")
        auth.authentication.logout()
        assert auth.authentication.authenticate("oper", "Reset123!").success

    def test_admin_reset_invalidates_target_session(self, initialized_database):
        auth = _auth(initialized_database)
        owner = _owner(auth)
        _login_owner(auth)
        # Resetting the current user's password should invalidate their session.
        auth.passwords.reset_admin(owner.user_id, "Reset123!", "Reset123!")
        assert not auth.session.is_authenticated

    def test_password_change_clears_reauthentication(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.session._session.reauthenticated_for.add("test")  # type: ignore[union-attr]
        auth.passwords.change_self("Owner123!", "NewPass1!", "NewPass1!")
        assert auth.session._session.reauthenticated_for == set()  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Authorization matrix
# ---------------------------------------------------------------------------


# Approved role grants from the matrix
EXPECTED_GRANTS = {
    RoleKey.OWNER_ADMIN: {
        PermissionKey.LOGOUT,
        PermissionKey.UNLOCK,
        PermissionKey.PASSWORD_CHANGE_SELF,
        PermissionKey.USER_CREATE,
        PermissionKey.USER_EDIT_IDENTITY,
        PermissionKey.USER_ACTIVATE,
        PermissionKey.USER_DEACTIVATE,
        PermissionKey.USER_RESET_PASSWORD,
        PermissionKey.USER_ASSIGN_ROLE,
        PermissionKey.PERMISSION_CHANGE,
        PermissionKey.SETTINGS_APPLICATION_UPDATE,
        PermissionKey.BACKUP_RESTORE,
        PermissionKey.DATABASE_RELOCATE,
        PermissionKey.AUDIT_VIEW,
        PermissionKey.AUDIT_EXPORT,
        PermissionKey.PARTY_VIEW,
        PermissionKey.PARTY_CREATE,
        PermissionKey.PARTY_EDIT,
    },
    RoleKey.OPERATOR: {
        PermissionKey.LOGOUT,
        PermissionKey.UNLOCK,
        PermissionKey.PASSWORD_CHANGE_SELF,
        PermissionKey.PARTY_VIEW,
        PermissionKey.PARTY_CREATE,
        PermissionKey.PARTY_EDIT,
    },
    RoleKey.ACCOUNTANT_REVIEWER: {
        PermissionKey.LOGOUT,
        PermissionKey.UNLOCK,
        PermissionKey.PASSWORD_CHANGE_SELF,
        PermissionKey.PARTY_VIEW,
    },
    RoleKey.VIEWER: {
        PermissionKey.LOGOUT,
        PermissionKey.UNLOCK,
        PermissionKey.PASSWORD_CHANGE_SELF,
        PermissionKey.PARTY_VIEW,
    },
}

# Permissions that must never be granted (not approved keys) - we only have
# approved keys in the enum; ensure LOGIN is not a role grant.
NEVER_ROLE_GRANTS = {PermissionKey.LOGIN}


class TestAuthorizationMatrix:
    @pytest.mark.parametrize("role", list(RoleKey))
    def test_role_permissions_match_matrix(self, role):
        from app.domain.auth import APPROVED_ROLE_PERMISSIONS

        granted = APPROVED_ROLE_PERMISSIONS[role]
        assert granted == EXPECTED_GRANTS[role]
        assert not (granted & NEVER_ROLE_GRANTS)

    @pytest.mark.parametrize("role", list(RoleKey))
    def test_runtime_permission_checks(self, initialized_database, role):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        # create a user with the target role and login as them
        uname = f"u_{role.value[:8]}"
        pwd = "UserPass1!"
        auth.users.create_user(uname, pwd, role, confirmation=pwd)
        auth.authentication.logout()
        res = auth.authentication.authenticate(uname, pwd)
        assert res.success
        for perm in PermissionKey:
            if perm in NEVER_ROLE_GRANTS:
                continue
            expected = perm in EXPECTED_GRANTS[role]
            assert auth.authorization.has_permission(perm) is expected, (
                f"{role} {perm} expected {expected}"
            )

    def test_unapproved_permission_key_denied(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        assert auth.authorization.has_permission("backup.create") is False
        assert auth.authorization.has_permission("unknown.permission") is False
        with pytest.raises(AuthorizationError):
            auth.authorization.require("backup.create")

    def test_direct_service_call_enforces_authz(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        auth.authentication.logout()
        _ = auth.authentication.authenticate("oper", "Operator1!")
        with pytest.raises(AuthorizationError):
            auth.users.create_user("x", "Xpass123!", RoleKey.VIEWER, confirmation="Xpass123!")
        with pytest.raises(AuthorizationError):
            auth.users.list_users()

    def test_last_active_admin_cannot_be_deactivated(self, initialized_database):
        auth = _auth(initialized_database)
        owner = _owner(auth)
        _login_owner(auth)
        with pytest.raises(DomainRuleError):
            auth.users.deactivate_user(owner.user_id)

    def test_last_active_admin_cannot_be_downgraded(self, initialized_database):
        auth = _auth(initialized_database)
        owner = _owner(auth)
        _login_owner(auth)
        with pytest.raises(DomainRuleError):
            auth.users.assign_role(owner.user_id, RoleKey.OPERATOR)

    def test_admin_can_deactivate_another_admin(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        second = auth.users.create_user(
            "admin2", "Admin123!", RoleKey.OWNER_ADMIN, confirmation="Admin123!"
        )
        deactivated = auth.users.deactivate_user(second.user_id)
        assert not deactivated.is_active

    def test_deactivated_user_session_invalidated(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        with initialized_database.unit_of_work() as work:
            op = UserAccountRepository(work.session).find_by_username("oper")
        # login as op in separate service instance sharing same DB
        op_auth = _auth(initialized_database)
        assert op_auth.authentication.authenticate("oper", "Operator1!").success
        assert op_auth.session.is_authenticated
        auth.users.deactivate_user(op.account.user_id)
        # op_auth session is separate in-memory object; but DB says inactive.
        # Authorization check should detect deactivation and end session.
        assert op_auth.authorization.has_permission(PermissionKey.LOGOUT) is False
        assert not op_auth.session.is_authenticated


# ---------------------------------------------------------------------------
# Session and idle lock
# ---------------------------------------------------------------------------


class TestSession:
    def test_session_creation_and_logout(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        assert auth.session.is_authenticated
        assert auth.session.identity is not None
        auth.authentication.logout()
        assert not auth.session.is_authenticated

    def test_idle_lock(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.session.configure_idle_timeout(1)
        # force last activity into past
        state = auth.session._session
        assert state is not None
        state.last_activity_at = "2000-01-01T00:00:00Z"
        assert auth.session.should_lock()
        assert auth.session.lock()
        assert auth.session.is_locked

    def test_locked_session_blocks_operations(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.session.lock()
        assert not auth.authorization.has_permission(PermissionKey.PASSWORD_CHANGE_SELF)
        with pytest.raises(AuthorizationError):
            auth.authorization.require(PermissionKey.PASSWORD_CHANGE_SELF)

    def test_unlock_with_correct_password(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.session.lock()
        result = auth.authentication.unlock("Owner123!")
        assert result.success
        assert not auth.session.is_locked

    def test_unlock_with_wrong_password_fails(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.session.lock()
        result = auth.authentication.unlock("wrong")
        assert not result.success
        assert auth.session.is_locked

    def test_close_while_locked_ends_session(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.session.lock()
        auth.session.end()
        assert not auth.session.is_authenticated
        assert auth.session.identity is None

    def test_role_change_takes_effect_at_next_authz_check(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        with initialized_database.unit_of_work() as work:
            op = UserAccountRepository(work.session).find_by_username("oper")
        op_auth = _auth(initialized_database)
        assert op_auth.authentication.authenticate("oper", "Operator1!").success
        assert not op_auth.authorization.has_permission(PermissionKey.USER_CREATE)
        # owner promotes op
        auth.users.assign_role(op.account.user_id, RoleKey.OWNER_ADMIN)
        # next authz check should see new role
        assert op_auth.authorization.has_permission(PermissionKey.USER_CREATE)

    def test_deactivation_invalidates_session_on_next_check(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        with initialized_database.unit_of_work() as work:
            op = UserAccountRepository(work.session).find_by_username("oper")
        op_auth = _auth(initialized_database)
        op_auth.authentication.authenticate("oper", "Operator1!")
        auth.users.deactivate_user(op.account.user_id)
        assert op_auth.authorization.has_permission(PermissionKey.LOGOUT) is False
        assert not op_auth.session.is_authenticated

    def test_default_idle_timeout(self):
        session = SessionService()
        assert session.idle_timeout_seconds == DEFAULT_IDLE_TIMEOUT_SECONDS

    def test_idle_timeout_must_be_positive(self):
        session = SessionService()
        with pytest.raises(SessionError):
            session.configure_idle_timeout(0)
        with pytest.raises(SessionError):
            session.configure_idle_timeout(-1)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class TestAudit:
    def _types(self, initialized_database):
        return [e.event_type for e in _audit_events(initialized_database)]

    def test_first_run_records_owner_created(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        events = _audit_events(initialized_database)
        created = [e for e in events if e.event_type == AuthEventType.OWNER_ACCOUNT_CREATED]
        assert len(created) == 1
        assert created[0].actor == UNAUTHENTICATED_ACTOR

    def test_login_success_and_failure_recorded(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        auth.authentication.authenticate("owner", "bad")
        auth.authentication.authenticate("owner", "Owner123!")
        types = self._types(initialized_database)
        assert AuthEventType.LOGIN_FAILED in types
        assert AuthEventType.LOGIN_SUCCEEDED in types

    def test_password_change_and_reset_are_distinct(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        with initialized_database.unit_of_work() as work:
            op = UserAccountRepository(work.session).find_by_username("oper")
        auth.passwords.change_self("Owner123!", "NewPass1!", "NewPass1!")
        # re-login after password change? session still authenticated; change_self keeps session.
        auth.passwords.reset_admin(op.account.user_id, "Reset123!", "Reset123!")
        types = self._types(initialized_database)
        assert AuthEventType.PASSWORD_CHANGED in types
        assert AuthEventType.PASSWORD_RESET_ADMIN in types
        assert AuthEventType.PASSWORD_CHANGED != AuthEventType.PASSWORD_RESET_ADMIN

    def test_account_lifecycle_events(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        user = auth.users.create_user(
            "oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!"
        )
        auth.users.assign_role(user.user_id, RoleKey.VIEWER)
        auth.users.deactivate_user(user.user_id)
        auth.users.activate_user(user.user_id)
        types = self._types(initialized_database)
        assert AuthEventType.USER_CREATED in types
        assert AuthEventType.ROLE_ASSIGNED in types
        assert AuthEventType.USER_DEACTIVATED in types
        assert AuthEventType.USER_ACTIVATED in types

    def test_lock_unlock_events(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        # The UI records lock events; record one here to test append-only storage.
        auth.session.lock()
        auth.audit.record(
            event_type=AuthEventType.LOCK,
            entity_type="session",
            entity_id=str(auth.session.identity.user_id) if auth.session.identity else "0",
            actor="user:1:owner",
            payload={},
        )
        auth.authentication.unlock("Owner123!")
        types = self._types(initialized_database)
        assert AuthEventType.LOCK in types
        assert AuthEventType.UNLOCK in types

    def test_actor_attribution(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        events = _audit_events(initialized_database)
        user_created = [e for e in events if e.event_type == AuthEventType.USER_CREATED][-1]
        assert user_created.actor.startswith("user:")
        assert "owner" in user_created.actor

    def test_audit_append_only_protections_intact(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        events = _audit_events(initialized_database)
        assert events
        with initialized_database.unit_of_work() as work:
            from sqlalchemy import select

            from app.infrastructure.database.models import AuditEventRecord

            record = work.session.scalar(select(AuditEventRecord))
            record.actor = "tampered"
            with pytest.raises(DomainRuleError):
                work.commit()

    def test_no_password_in_audit_payloads(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth, password="Secret123!")
        _login_owner(auth, password="Secret123!")
        auth.passwords.change_self("Secret123!", "NewPass1!", "NewPass1!")
        for event in _audit_events(initialized_database):
            payload = event.payload or ""
            assert "Secret123!" not in payload
            assert "NewPass1!" not in payload

    def test_rename_user_audited(self, initialized_database):
        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        user = auth.users.create_user(
            "oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!"
        )
        auth.users.rename_user(user.user_id, "operator2")
        types = self._types(initialized_database)
        assert AuthEventType.USER_UPDATED in types


class TestServiceAuthz:
    def test_restore_requires_permission(self, initialized_database, tmp_path):
        from types import SimpleNamespace

        from app.core.config import ConfigService
        from app.infrastructure.backup.directories import BackupDirectories
        from app.infrastructure.backup.lock import OperationLock
        from app.infrastructure.backup.state import BackupStateStore
        from app.infrastructure.filesystem.layout import DataRootLayout
        from app.services.database_runtime import DatabaseRuntime
        from app.services.restore_service import RestoreService

        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        auth.authentication.logout()
        auth.authentication.authenticate("oper", "Operator1!")
        layout = DataRootLayout(tmp_path / "data")
        dirs = BackupDirectories.from_layout(layout)
        dirs.ensure()
        runtime = DatabaseRuntime()
        runtime.install(initialized_database)
        svc = RestoreService(
            config_service=ConfigService(tmp_path / "cfg.json"),
            runtime=runtime,
            directories=dirs,
            lock=OperationLock(dirs.lock_path, operation="restore"),
            backup_service=None,
            expected_schema_revision="x",
            state_store=BackupStateStore(dirs.state_path),
            auth_services=auth,
        )
        with pytest.raises(AuthorizationError):
            svc.restore(SimpleNamespace())

    def test_relocation_requires_permission(self, initialized_database, tmp_path):
        from app.core.config import ConfigService
        from app.infrastructure.backup.lock import OperationLock
        from app.infrastructure.filesystem.layout import DataRootLayout
        from app.services.database_runtime import DatabaseRuntime
        from app.services.relocation_service import RelocationService

        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        auth.authentication.logout()
        auth.authentication.authenticate("oper", "Operator1!")
        layout = DataRootLayout(tmp_path / "data")
        layout.backups_dir.mkdir(parents=True, exist_ok=True)
        lock = OperationLock(layout.backups_dir / "Backup.lock", operation="relocation")
        runtime = DatabaseRuntime()
        runtime.install(initialized_database)
        from app.infrastructure.backup.state import BackupStateStore
        from app.infrastructure.filesystem.validation import DataLocationValidator

        svc = RelocationService(
            config_service=ConfigService(tmp_path / "cfg.json"),
            runtime=runtime,
            lock=lock,
            backup_service=None,
            validator=DataLocationValidator(),
            state_store=BackupStateStore(layout.backups_dir / "state.json"),
            auth_services=auth,
        )
        with pytest.raises(AuthorizationError):
            svc.relocate(tmp_path / "other")

    def test_schedule_requires_permission(self, initialized_database, tmp_path):
        from app.core.config import ConfigService
        from app.services.schedule_service import ScheduleService

        auth = _auth(initialized_database)
        _owner(auth)
        _login_owner(auth)
        auth.users.create_user("oper", "Operator1!", RoleKey.OPERATOR, confirmation="Operator1!")
        auth.authentication.logout()
        auth.authentication.authenticate("oper", "Operator1!")
        cfg = ConfigService(tmp_path / "cfg.json")
        svc = ScheduleService(cfg, auth_services=auth)
        with pytest.raises(AuthorizationError):
            svc.update_settings(enabled=True, time="09:00", retention_days=30, keep_minimum=14)
