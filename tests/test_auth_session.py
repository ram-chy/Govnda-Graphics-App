"""Session, idle-lock, and background-work restriction tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import AuthorizationError, SessionError
from app.domain.auth import PermissionKey, RoleKey, SessionIdentity
from app.services.auth_services import AuthServices
from app.services.session_service import SessionService

IDENTITY = SessionIdentity(user_id=1, username="Owner1", role_key=RoleKey.OWNER_ADMIN)


def _old_timestamp(hours: int = 2) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def test_session_start_and_logout(auth_services) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    assert auth_services.session.is_authenticated
    assert auth_services.session.identity is not None

    auth.logout()
    assert not auth_services.session.is_authenticated
    assert auth_services.session.identity is None
    with pytest.raises(SessionError):
        auth_services.session.require_identity()


def test_idle_timeout_uses_configurable_duration() -> None:
    session = SessionService(clock=_old_timestamp)
    session.start(IDENTITY)
    session.configure_idle_timeout(60)

    assert session.should_lock()
    assert session.idle_seconds() >= 3600


def test_deliberate_activity_resets_idle_timer() -> None:
    clock_value = [_old_timestamp()]
    session = SessionService(clock=lambda: clock_value[0])
    session.start(IDENTITY)
    session.configure_idle_timeout(60)
    assert session.should_lock()

    clock_value[0] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    session.touch()
    assert not session.should_lock()


def test_lock_unlock_and_locked_identity_access() -> None:
    session = SessionService()
    session.start(IDENTITY)

    assert session.lock()
    assert session.is_locked
    assert not session.lock()
    with pytest.raises(SessionError):
        session.require_identity()
    session.touch()
    assert session.idle_seconds() >= 0

    assert session.unlock()
    assert not session.is_locked
    assert not session.unlock()
    assert session.require_identity() == IDENTITY


def test_lock_clears_temporary_reauthentication_state() -> None:
    session = SessionService()
    session.start(IDENTITY)
    assert session.lock()
    assert session.unlock()
    assert session._session is not None
    assert session._session.reauthenticated_for == set()


def test_close_while_locked_ends_session_without_persistence(
    auth_services, initialized_database
) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    assert auth_services.session.lock()

    auth_services.session.end()
    assert not auth_services.session.is_authenticated

    restarted = AuthServices.create(initialized_database)
    assert not restarted.session.is_authenticated
    assert not restarted.session.is_locked


def test_locked_session_blocks_sensitive_services(auth_services) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    assert auth_services.session.lock()

    with pytest.raises(AuthorizationError):
        auth_services.users.list_users()
    with pytest.raises(AuthorizationError):
        auth_services.passwords.reset_admin(1, "ResetPass3", "ResetPass3")
    assert not auth_services.authorization.has_permission(PermissionKey.BACKUP_RESTORE)


def test_idle_timeout_rejects_non_positive_values(auth_services) -> None:
    with pytest.raises(SessionError):
        auth_services.session.configure_idle_timeout(0)
    with pytest.raises(SessionError):
        auth_services.session.configure_idle_timeout(-5)
