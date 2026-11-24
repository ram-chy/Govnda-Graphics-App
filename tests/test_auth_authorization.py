"""Authorization matrix and service-layer enforcement tests."""

from __future__ import annotations

import pytest

from app.core.exceptions import AuthorizationError, DomainRuleError
from app.domain.auth import (
    APPROVED_ROLE_PERMISSIONS,
    PermissionKey,
    RoleKey,
    UserAccount,
)
from app.infrastructure.database.auth_repository import UserAccountRepository
from app.services.sensitive_operations import SensitiveOperationService

ADMIN_PERMISSIONS = frozenset(
    permission for permission in PermissionKey if permission is not PermissionKey.LOGIN
)
SELF_SERVICE = frozenset(
    {
        PermissionKey.LOGOUT,
        PermissionKey.UNLOCK,
        PermissionKey.PASSWORD_CHANGE_SELF,
    }
)
OPERATOR_PERMISSIONS = frozenset(
    {
        *SELF_SERVICE,
        PermissionKey.PARTY_VIEW,
        PermissionKey.PARTY_CREATE,
        PermissionKey.PARTY_EDIT,
        PermissionKey.CATALOGUE_VIEW,
        PermissionKey.CATALOGUE_CREATE,
        PermissionKey.CATALOGUE_EDIT,
    }
)
REVIEWER_OR_VIEWER_PERMISSIONS = frozenset(
    {
        *SELF_SERVICE,
        PermissionKey.PARTY_VIEW,
        PermissionKey.CATALOGUE_VIEW,
    }
)


def _login_owner(auth_services) -> UserAccount:
    account = auth_services.authentication.create_first_run_owner(
        "Owner1", "Password1", confirmation="Password1"
    )
    assert auth_services.authentication.authenticate("Owner1", "Password1").success
    return account


def test_approved_role_permission_matrix() -> None:
    assert set(APPROVED_ROLE_PERMISSIONS) == set(RoleKey)
    assert APPROVED_ROLE_PERMISSIONS[RoleKey.OWNER_ADMIN] == ADMIN_PERMISSIONS
    assert APPROVED_ROLE_PERMISSIONS[RoleKey.OPERATOR] == OPERATOR_PERMISSIONS
    assert (
        APPROVED_ROLE_PERMISSIONS[RoleKey.ACCOUNTANT_REVIEWER]
        == REVIEWER_OR_VIEWER_PERMISSIONS
    )
    assert APPROVED_ROLE_PERMISSIONS[RoleKey.VIEWER] == REVIEWER_OR_VIEWER_PERMISSIONS


def test_every_role_against_every_implemented_permission(auth_services) -> None:
    _login_owner(auth_services)
    for role in RoleKey:
        auth_services.users.create_user(
            f"user{role.value}", "Password1", role, confirmation="Password1"
        )

    for role in RoleKey:
        username = f"user{role.value}"
        auth_services.session.end()
        assert auth_services.authentication.authenticate(username, "Password1").success
        expected = APPROVED_ROLE_PERMISSIONS[role]
        for permission in PermissionKey:
            assert auth_services.authorization.has_permission(permission) is (
                permission in expected
            ), f"{role.value}/{permission.value}"


def test_unapproved_permissions_are_denied_by_default(auth_services) -> None:
    _login_owner(auth_services)
    auth_services.authentication.authenticate("Owner1", "Password1")

    assert not auth_services.authorization.has_permission("sales.create")
    assert not auth_services.authorization.has_permission("audit.modify")
    with pytest.raises(AuthorizationError):
        auth_services.authorization.require("sales.create")


def test_service_layer_cannot_be_bypassed_by_ui_state(auth_services) -> None:
    _login_owner(auth_services)
    auth_services.users.create_user(
        "Viewer1", "Password1", RoleKey.VIEWER, confirmation="Password1"
    )
    auth_services.session.end()
    assert auth_services.authentication.authenticate("Viewer1", "Password1").success

    with pytest.raises(AuthorizationError):
        auth_services.users.create_user(
            "Sneaky", "Password1", RoleKey.OWNER_ADMIN, confirmation="Password1"
        )
    with pytest.raises(AuthorizationError):
        auth_services.users.list_users()
    with pytest.raises(AuthorizationError):
        auth_services.passwords.reset_admin(1, "ResetPass3", "ResetPass3")


def test_last_active_admin_protection(auth_services) -> None:
    owner = _login_owner(auth_services)
    auth_services.authentication.authenticate("Owner1", "Password1")

    with pytest.raises(DomainRuleError):
        auth_services.users.deactivate_user(owner.user_id)
    with pytest.raises(DomainRuleError):
        auth_services.users.assign_role(owner.user_id, RoleKey.VIEWER)

    auth_services.users.create_user(
        "Admin2", "Password2", RoleKey.OWNER_ADMIN, confirmation="Password2"
    )
    auth_services.users.assign_role(owner.user_id, RoleKey.VIEWER)
    assert auth_services.session.role_key is RoleKey.VIEWER
    assert not auth_services.authorization.has_permission(PermissionKey.USER_ASSIGN_ROLE)


def test_deactivated_user_session_is_invalidated(auth_services) -> None:
    owner = _login_owner(auth_services)
    auth_services.authentication.authenticate("Owner1", "Password1")
    auth_services.users.create_user(
        "Admin2", "Password2", RoleKey.OWNER_ADMIN, confirmation="Password2"
    )

    auth_services.users.deactivate_user(owner.user_id)
    assert not auth_services.session.is_authenticated
    assert not auth_services.authorization.has_permission(PermissionKey.USER_CREATE)


def test_role_change_is_visible_on_next_permission_check(
    auth_services, initialized_database
) -> None:
    owner = _login_owner(auth_services)
    auth_services.authentication.authenticate("Owner1", "Password1")
    assert auth_services.authorization.has_permission(PermissionKey.USER_CREATE)

    with initialized_database.unit_of_work() as work:
        UserAccountRepository(work.session).set_role(owner.user_id, role_key=RoleKey.VIEWER)
        work.commit()

    assert not auth_services.authorization.has_permission(PermissionKey.USER_CREATE)
    assert auth_services.authorization.has_permission(PermissionKey.LOGOUT)


def test_sensitive_operation_gate_enforces_authorization(auth_services) -> None:
    _login_owner(auth_services)
    auth_services.authentication.authenticate("Owner1", "Password1")
    gate = SensitiveOperationService(
        auth_services.authorization, auth_services.session, auth_services.audit
    )

    assert gate.allows(PermissionKey.BACKUP_RESTORE)
    gate.require(PermissionKey.BACKUP_RESTORE)
    auth_services.users.create_user(
        "Viewer1", "Password1", RoleKey.VIEWER, confirmation="Password1"
    )
    auth_services.session.end()
    assert auth_services.authentication.authenticate("Viewer1", "Password1").success
    assert not gate.allows(PermissionKey.BACKUP_RESTORE)
    with pytest.raises(AuthorizationError):
        gate.require(PermissionKey.BACKUP_RESTORE)
