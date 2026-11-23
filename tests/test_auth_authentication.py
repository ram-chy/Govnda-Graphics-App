"""Authentication workflow tests against isolated temporary databases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ConflictError, ValidationError
from app.domain.auth import (
    GENERIC_AUTH_FAILURE,
    RoleKey,
    validate_password,
    validate_username,
)
from app.infrastructure.database.auth_repository import COOLDOWN_SECONDS, UserAccountRepository
from app.services.authentication_service import AuthenticationService


def _stored_hash(database, user_id: int) -> str:
    with database.unit_of_work() as work:
        stored = UserAccountRepository(work.session).get(user_id)
        assert stored is not None
        return stored.password_hash


def test_first_run_owner_creation(auth_services, initialized_database) -> None:
    auth = auth_services.authentication
    assert not auth.has_accounts()

    account = auth.create_first_run_owner(
        "Owner1", "Password1", email="owner@example.test", confirmation="Password1"
    )
    assert account.role_key is RoleKey.OWNER_ADMIN
    assert account.is_active
    assert account.email == "owner@example.test"
    assert auth.has_accounts()

    stored_hash = _stored_hash(initialized_database, account.user_id)
    assert "Password1" not in stored_hash
    assert stored_hash.startswith("$argon2id$") or stored_hash.startswith("scrypt$")


def test_first_run_cannot_be_repeated_or_duplicated_case_insensitively(
    auth_services,
) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")

    with pytest.raises(ConflictError):
        auth.create_first_run_owner("Another", "Password1", confirmation="Password1")

    auth.authenticate("Owner1", "Password1")
    with pytest.raises(ConflictError):
        auth_services.users.create_user(
            "owner1", "Password1", RoleKey.VIEWER, confirmation="Password1"
        )


def test_login_success_and_generic_failure(auth_services) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")

    result = auth.authenticate("Owner1", "Password1")
    assert result.success
    assert result.identity is not None
    assert result.identity.role_key is RoleKey.OWNER_ADMIN
    assert auth_services.session.is_authenticated

    auth_services.session.end()
    failed = auth.authenticate("Owner1", "WrongPass1")
    assert not failed.success
    assert failed.message == GENERIC_AUTH_FAILURE
    assert failed.identity is None

    unknown = auth.authenticate("NoSuchUser", "Password1")
    assert not unknown.success
    assert unknown.message == GENERIC_AUTH_FAILURE


def test_login_is_case_insensitive_for_username(auth_services) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    auth_services.session.end()

    assert auth.authenticate("  OWNER1  ", "Password1").success


def test_deactivated_account_cannot_login(auth_services) -> None:
    auth = auth_services.authentication
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success
    owner_id = auth_services.session.identity.user_id  # type: ignore[union-attr]
    auth_services.users.create_user(
        "Admin2", "Password2", RoleKey.OWNER_ADMIN, confirmation="Password2"
    )
    auth_services.users.deactivate_user(owner_id)
    auth_services.session.end()

    result = auth.authenticate("Owner1", "Password1")
    assert not result.success
    assert result.message == GENERIC_AUTH_FAILURE


def test_failed_login_cooldown_and_expiration(auth_services, initialized_database) -> None:
    current = [datetime(2026, 11, 23, 10, 0, tzinfo=UTC)]
    auth = AuthenticationService(
        initialized_database,
        auth_services.hasher,
        auth_services.session,
        auth_services.audit,
        now=lambda: current[0],
    )
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")

    for _ in range(5):
        assert not auth.authenticate("Owner1", "WrongPass1").success

    throttled = auth.authenticate("Owner1", "Password1")
    assert not throttled.success
    assert throttled.cooldown_remaining_seconds > 0

    current[0] += timedelta(seconds=COOLDOWN_SECONDS + 1)
    assert auth.authenticate("Owner1", "Password1").success


def test_successful_login_clears_throttle_state(auth_services, initialized_database) -> None:
    current = [datetime(2026, 11, 23, 10, 0, tzinfo=UTC)]
    auth = AuthenticationService(
        initialized_database,
        auth_services.hasher,
        auth_services.session,
        auth_services.audit,
        now=lambda: current[0],
    )
    auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    for _ in range(3):
        auth.authenticate("Owner1", "WrongPass1")
    assert auth.authenticate("Owner1", "Password1").success
    auth_services.session.end()

    assert auth.authenticate("Owner1", "Password1").success


def test_password_policy_validation() -> None:
    assert not validate_password("short").valid
    assert not validate_password("nouppercase1").valid
    assert not validate_password("NOLOWERCASE1").valid
    assert not validate_password("NoDigitsHere").valid
    assert not validate_password("Password1", "Mismatch1").valid
    assert validate_password("Password1", "Password1").valid

    assert not validate_username("ab").valid
    assert not validate_username("has space").valid
    assert validate_username("Owner1").valid


def test_password_change_and_administrative_reset(auth_services) -> None:
    auth = auth_services.authentication
    account = auth.create_first_run_owner("Owner1", "Password1", confirmation="Password1")
    assert auth.authenticate("Owner1", "Password1").success

    with pytest.raises(ValidationError):
        auth_services.passwords.change_self("WrongPass1", "NewPass12", "NewPass12")

    auth_services.passwords.change_self("Password1", "NewPass12", "NewPass12")
    auth_services.session.end()
    assert auth.authenticate("Owner1", "NewPass12").success

    auth_services.passwords.reset_admin(account.user_id, "ResetPass3", "ResetPass3")
    assert not auth_services.session.is_authenticated
    assert auth.authenticate("Owner1", "ResetPass3").success
    assert not auth.authenticate("Owner1", "NewPass12").success
