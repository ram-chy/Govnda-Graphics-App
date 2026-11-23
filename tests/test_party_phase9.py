"""Phase 9: Customer & Supplier master data tests."""

from __future__ import annotations

import pytest

from app.domain.auth import RoleKey
from app.domain.party import (
    Party,
    PartyKind,
    normalize_party_name,
    normalize_phone,
    party_name_key,
    validate_party,
)
from app.infrastructure.database.party_repository import PartyRepository
from app.services.auth_services import AuthServices
from app.services.database_runtime import DatabaseRuntime
from app.services.party_service import PartyService


def _runtime(initialized_database):
    runtime = DatabaseRuntime()
    runtime.install(initialized_database)
    return runtime


def _owner(auth: AuthServices, username: str = "owner", password: str = "Owner123!") -> None:
    auth.authentication.create_first_run_owner(username, password, confirmation=password)
    result = auth.authentication.authenticate(username, password)
    assert result.success, result.message


def _add_user(auth: AuthServices, username: str, role: RoleKey, password: str = "User123!") -> None:
    # Owner must be logged in.
    account = auth.users.create_user(
        username=username,
        password=password,
        confirmation=password,
        role_key=role,
    )
    assert account.username == username


def _login(auth: AuthServices, username: str, password: str = "User123!") -> None:
    auth.session.end()
    result = auth.authentication.authenticate(username, password)
    assert result.success, result.message


def _audit_events(initialized_database):
    from app.infrastructure.database.business_profile_repository import AuditEventRepository

    with initialized_database.unit_of_work() as work:
        return AuditEventRepository(work.session).list()


class TestPartyDomain:
    def test_normalization(self):
        assert normalize_party_name("  Acme   Graphics  ") == "Acme Graphics"
        assert party_name_key("  Acme   Graphics  ") == "acme graphics"
        assert normalize_phone("  017  11  ") == "017 11"

    def test_validation_requires_name(self):
        result = validate_party(Party(party_id=None, kind=PartyKind.CUSTOMER, name="  "))
        assert not result.valid
        assert any("Name is required" in e for e in result.errors)

    def test_validation_rejects_long_fields(self):
        result = validate_party(
            Party(party_id=None, kind=PartyKind.SUPPLIER, name="A", phone="1" * 51)
        )
        assert not result.valid
        assert any("Phone" in e for e in result.errors)


class TestPartyRepository:
    def test_create_list_update(self, initialized_database):
        with initialized_database.unit_of_work() as work:
            repo = PartyRepository(work.session)
            created = repo.create(
                Party(party_id=None, kind=PartyKind.CUSTOMER, name="Acme", phone="123")
            )
            work.commit()
        assert created.party_id is not None
        assert created.name == "Acme"

        with initialized_database.unit_of_work() as work:
            repo = PartyRepository(work.session)
            listed = repo.list(PartyKind.CUSTOMER)
            assert len(listed) == 1
            updated = repo.update(
                Party(
                    party_id=created.party_id,
                    kind=PartyKind.CUSTOMER,
                    name="Acme Updated",
                    phone="123",
                    is_active=True,
                )
            )
            work.commit()
        assert updated.name == "Acme Updated"

    def test_duplicate_detection(self, initialized_database):
        with initialized_database.unit_of_work() as work:
            repo = PartyRepository(work.session)
            repo.create(Party(party_id=None, kind=PartyKind.CUSTOMER, name="Acme", phone="0171"))
            work.commit()

        with initialized_database.unit_of_work() as work:
            repo = PartyRepository(work.session)
            name_dupes = repo.find_name_duplicates(PartyKind.CUSTOMER, " acme ")
            phone_dupes = repo.find_phone_duplicates(PartyKind.CUSTOMER, "0171")
            assert len(name_dupes) == 1
            assert len(phone_dupes) == 1
            # Different kind should not match
            assert repo.find_name_duplicates(PartyKind.SUPPLIER, "acme") == ()

    def test_search_and_active_filter(self, initialized_database):
        with initialized_database.unit_of_work() as work:
            repo = PartyRepository(work.session)
            repo.create(Party(party_id=None, kind=PartyKind.SUPPLIER, name="Alpha", is_active=True))
            repo.create(Party(party_id=None, kind=PartyKind.SUPPLIER, name="Beta", is_active=False))
            work.commit()

        with initialized_database.unit_of_work() as work:
            repo = PartyRepository(work.session)
            all_rows = repo.list(PartyKind.SUPPLIER)
            active_only = repo.list(PartyKind.SUPPLIER, include_inactive=False)
            search = repo.list(PartyKind.SUPPLIER, search="alp")
            assert len(all_rows) == 2
            assert len(active_only) == 1
            assert active_only[0].name == "Alpha"
            assert len(search) == 1


class TestPartyService:
    def test_create_warns_on_duplicate_and_saves_on_confirm(
        self, initialized_database, auth_services
    ):
        _owner(auth_services)
        runtime = _runtime(initialized_database)
        service = PartyService(runtime, auth_services=auth_services)

        first = service.save_party(
            Party(party_id=None, kind=PartyKind.CUSTOMER, name="Acme", phone="123")
        )
        assert first.success

        warned = service.save_party(
            Party(party_id=None, kind=PartyKind.CUSTOMER, name="Acme", phone="123")
        )
        assert not warned.success
        assert warned.warnings
        assert "duplicate" in warned.message.lower() or "Duplicate" in warned.warnings[0].reason

        confirmed = service.save_party(
            Party(party_id=None, kind=PartyKind.CUSTOMER, name="Acme", phone="123"),
            confirm_duplicates=True,
        )
        assert confirmed.success
        assert confirmed.party is not None

    def test_update_and_deactivate_audit(self, initialized_database, auth_services):
        _owner(auth_services)
        runtime = _runtime(initialized_database)
        service = PartyService(runtime, auth_services=auth_services)

        created = service.save_party(
            Party(party_id=None, kind=PartyKind.SUPPLIER, name="Vendor", is_active=True)
        )
        assert created.success and created.party is not None

        updated = service.save_party(
            Party(
                party_id=created.party.party_id,
                kind=PartyKind.SUPPLIER,
                name="Vendor Updated",
                is_active=False,
            ),
            confirm_duplicates=True,
        )
        assert updated.success
        assert updated.party is not None
        assert updated.party.is_active is False

        events = _audit_events(initialized_database)
        types = [e.event_type for e in events]
        assert "party.created" in types
        assert "party.updated" in types
        assert "party.deactivated" in types

    def test_activate_reactivate(self, initialized_database, auth_services):
        _owner(auth_services)
        runtime = _runtime(initialized_database)
        service = PartyService(runtime, auth_services=auth_services)
        created = service.save_party(
            Party(party_id=None, kind=PartyKind.CUSTOMER, name="A", is_active=True)
        )
        assert created.party is not None
        pid = created.party.party_id
        assert pid is not None

        deactivated = service.set_active(pid, active=False)
        assert deactivated.success
        assert deactivated.party is not None
        assert not deactivated.party.is_active
        activated = service.set_active(pid, active=True)
        assert activated.success
        assert activated.party is not None
        assert activated.party.is_active

    def test_role_authorization(self, initialized_database, auth_services):
        _owner(auth_services)
        _add_user(auth_services, "operator", RoleKey.OPERATOR)
        _add_user(auth_services, "acctrev", RoleKey.ACCOUNTANT_REVIEWER)
        _add_user(auth_services, "viewer1", RoleKey.VIEWER)

        runtime = _runtime(initialized_database)
        service = PartyService(runtime, auth_services=auth_services)

        _login(auth_services, "operator")
        op = service.save_party(Party(party_id=None, kind=PartyKind.CUSTOMER, name="OpCust"))
        assert op.success

        _login(auth_services, "acctrev")
        from app.core.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            service.save_party(Party(party_id=None, kind=PartyKind.CUSTOMER, name="Nope"))
        rows = service.list_parties(PartyKind.CUSTOMER)
        assert any(p.name == "OpCust" for p in rows)

        _login(auth_services, "viewer1")
        with pytest.raises(AuthorizationError):
            service.save_party(Party(party_id=None, kind=PartyKind.CUSTOMER, name="Nope2"))
        rows = service.list_parties(PartyKind.CUSTOMER)
        assert len(rows) >= 1

    def test_no_hard_delete_api(self):
        assert not hasattr(PartyService, "delete")
        assert not hasattr(PartyService, "delete_party")


class TestPartyMigrationSmoke:
    def test_parties_table_exists(self, initialized_database):
        with initialized_database.engine.connect() as conn:
            rows = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='parties'"
            ).fetchall()
        assert len(rows) == 1
