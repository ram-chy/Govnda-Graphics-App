"""Append-only audit coverage for authentication and administration events."""

from __future__ import annotations

import json

import pytest

from app.core.exceptions import MigrationError
from app.domain.auth import AdminEventType, AuthEventType, RoleKey
from app.infrastructure.database.audit_history import read_audit_rows
from app.infrastructure.database.migrations import MigrationManager, application_head_revision
from app.services.auth_support import actor_payload
from app.services.sensitive_operations import SensitiveOperationService


def _events(database) -> tuple[object, ...]:
    return read_audit_rows(database.config.path)


def _types(database) -> list[str]:
    return [row.event_type for row in _events(database)]


def _payload(database, event_type: str) -> dict[str, object]:
    for row in _events(database):
        if row.event_type == event_type:
            return json.loads(row.payload)
    raise AssertionError(f"missing audit event: {event_type}")


def test_first_run_and_login_events_are_recorded(auth_services, initialized_database) -> None:
    auth = auth_services.authentication
    account = auth.create_first_run_owner(
        "Owner1", "Password1", email="owner@example.test", confirmation="Password1"
    )
    assert auth.authenticate("Owner1", "Password1").success

    events = _types(initialized_database)
    assert AuthEventType.OWNER_ACCOUNT_CREATED in events
    assert AuthEventType.LOGIN_SUCCEEDED in events
    created = next(
        row
        for row in _events(initialized_database)
        if row.event_type == AuthEventType.OWNER_ACCOUNT_CREATED
    )
    assert created.entity_id == str(account.user_id)
    assert created.actor == "system/unauthenticated"
    assert created.payload == '{"role":"owner_admin","username":"Owner1"}'
    assert "Password1" not in created.payload


def test_failed_login_is_audited_without_credentials(auth_services, initialized_database) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")

    assert not auth.authenticate("Owner1", "WrongPass1").success
    row = next(
        row for row in _events(initialized_database) if row.event_type == AuthEventType.LOGIN_FAILED
    )
    assert row.actor == "system/unauthenticated"
    assert "WrongPass1" not in row.payload
    assert "Password1" not in row.payload
    assert json.loads(row.payload)["reason"] == "invalid_credentials"


def test_account_lifecycle_events_record_authenticated_actor(
    auth_services, initialized_database
) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    actor = auth_services.session.actor

    created = auth_services.users.create_user(
        "Viewer1", "Password1", RoleKey.VIEWER, confirmation="Password1"
    )
    auth_services.users.assign_role(created.user_id, RoleKey.OPERATOR)
    auth_services.users.set_email(created.user_id, "viewer@example.test")
    auth_services.users.deactivate_user(created.user_id)
    auth_services.users.activate_user(created.user_id)

    events = _types(initialized_database)
    for event_type in (
        AuthEventType.USER_CREATED,
        AuthEventType.ROLE_ASSIGNED,
        AuthEventType.USER_UPDATED,
        AuthEventType.USER_DEACTIVATED,
        AuthEventType.USER_ACTIVATED,
    ):
        assert event_type in events
    rows = [row for row in _events(initialized_database) if row.actor == actor]
    assert len(rows) >= 5
    assert all("Password1" not in row.payload for row in rows)


def test_password_events_are_separate(auth_services, initialized_database) -> None:
    auth = auth_services.authentication
    owner = auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success

    auth_services.passwords.change_self("Password1", "NewPass12", "NewPass12")
    auth_services.session.end()
    assert auth.authenticate("Owner1", "NewPass12").success
    auth_services.passwords.reset_admin(owner.user_id, "ResetPass3", "ResetPass3")

    events = _types(initialized_database)
    assert events.count(AuthEventType.PASSWORD_CHANGED) == 1
    assert events.count(AuthEventType.PASSWORD_RESET_ADMIN) == 1
    assert "NewPass12" not in "\n".join(row.payload for row in _events(initialized_database))
    assert "ResetPass3" not in "\n".join(row.payload for row in _events(initialized_database))


def test_lock_unlock_and_logout_events(auth_services, initialized_database) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    actor = auth_services.session.actor

    assert auth_services.session.lock()
    auth_services.audit.record(
        event_type=AuthEventType.LOCK,
        entity_type="session",
        entity_id="1",
        actor=actor,
        payload=actor_payload(auth_services.session),
    )
    assert auth.unlock("Password1").success

    auth.logout()
    events = _types(initialized_database)
    assert AuthEventType.LOCK in events
    assert AuthEventType.UNLOCK in events
    assert AuthEventType.LOGOUT in events


def test_administrative_actions_record_authenticated_actor(
    auth_services, initialized_database
) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    actor = auth_services.session.actor
    gate = SensitiveOperationService(
        auth_services.authorization, auth_services.session, auth_services.audit
    )

    gate.record(
        event_type=AdminEventType.BACKUP_RESTORED,
        entity_type="administration",
        entity_id="1",
        payload={"backup": "test"},
    )
    row = next(
        row
        for row in _events(initialized_database)
        if row.event_type == AdminEventType.BACKUP_RESTORED
    )
    assert row.actor == actor
    assert json.loads(row.payload) == {"backup": "test"}


def test_audit_rows_are_append_only_and_protect_downgrade(
    auth_services, initialized_database
) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    before = [row.id for row in _events(initialized_database)]
    assert len(before) >= 2

    manager = MigrationManager(initialized_database)
    with pytest.raises(MigrationError, match="audit history"):
        manager.downgrade("0003_business_profile_requirements")

    assert manager.current_revision() == application_head_revision()
    assert [row.id for row in _events(initialized_database)] == before
