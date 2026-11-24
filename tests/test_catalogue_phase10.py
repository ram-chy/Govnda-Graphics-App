"""Phase 10: Product & Service catalogue tests."""

from __future__ import annotations

import pytest

from app.core.exceptions import AuthorizationError
from app.domain.auth import RoleKey
from app.domain.catalogue import (
    CatalogueItem,
    CatalogueKind,
    catalogue_name_key,
    normalize_catalogue_name,
    validate_catalogue_item,
)
from app.infrastructure.database.catalogue_repository import CatalogueRepository
from app.infrastructure.database.migrations import MigrationManager
from app.services.auth_services import AuthServices
from app.services.catalogue_service import CatalogueService
from app.services.database_runtime import DatabaseRuntime


def _runtime(initialized_database):
    runtime = DatabaseRuntime()
    runtime.install(initialized_database)
    return runtime


def _owner(auth: AuthServices, username: str = "owner", password: str = "Owner123!") -> None:
    auth.authentication.create_first_run_owner(username, password, confirmation=password)
    result = auth.authentication.authenticate(username, password)
    assert result.success, result.message


def _add_user(auth: AuthServices, username: str, role: RoleKey, password: str = "User123!") -> None:
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


class TestCatalogueDomain:
    def test_normalization(self):
        assert normalize_catalogue_name("  Business   Card  ") == "Business Card"
        assert catalogue_name_key("  Business   Card  ") == "business card"

    def test_validation_requires_name(self):
        result = validate_catalogue_item(
            CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name="  ")
        )
        assert not result.valid
        assert any("Name is required" in e for e in result.errors)

    def test_validation_rejects_bad_fields(self):
        result = validate_catalogue_item(
            CatalogueItem(
                item_id=None,
                kind=CatalogueKind.SERVICE,
                name="A",
                unit="u" * 101,
                description="d" * 501,
                default_sale_price_minor=-1,
            )
        )
        assert not result.valid
        assert any("Unit" in e for e in result.errors)
        assert any("Description" in e for e in result.errors)
        assert any("negative" in e.lower() for e in result.errors)

    def test_validation_accepts_reference_price(self):
        result = validate_catalogue_item(
            CatalogueItem(
                item_id=None,
                kind=CatalogueKind.PRODUCT,
                name="Banner",
                default_sale_price_minor=15050,
            )
        )
        assert result.valid


class TestCatalogueRepository:
    def test_create_list_update(self, initialized_database):
        with initialized_database.unit_of_work() as work:
            repo = CatalogueRepository(work.session)
            created = repo.create(
                CatalogueItem(
                    item_id=None,
                    kind=CatalogueKind.PRODUCT,
                    name="Banner",
                    unit="sq ft",
                    default_sale_price_minor=5000,
                )
            )
            work.commit()
        assert created.item_id is not None
        assert created.name == "Banner"

        with initialized_database.unit_of_work() as work:
            repo = CatalogueRepository(work.session)
            listed = repo.list(CatalogueKind.PRODUCT)
            assert len(listed) == 1
            updated = repo.update(
                CatalogueItem(
                    item_id=created.item_id,
                    kind=CatalogueKind.PRODUCT,
                    name="Banner Updated",
                    unit="sq ft",
                    default_sale_price_minor=6000,
                    is_active=True,
                )
            )
            work.commit()
        assert updated.name == "Banner Updated"
        assert updated.default_sale_price_minor == 6000

    def test_duplicate_detection_within_kind(self, initialized_database):
        with initialized_database.unit_of_work() as work:
            repo = CatalogueRepository(work.session)
            repo.create(CatalogueItem(item_id=None, kind=CatalogueKind.SERVICE, name="Design"))
            work.commit()

        with initialized_database.unit_of_work() as work:
            repo = CatalogueRepository(work.session)
            dupes = repo.find_name_duplicates(CatalogueKind.SERVICE, " design ")
            assert len(dupes) == 1
            assert repo.find_name_duplicates(CatalogueKind.PRODUCT, "Design") == ()

    def test_search_and_active_filter(self, initialized_database):
        with initialized_database.unit_of_work() as work:
            repo = CatalogueRepository(work.session)
            repo.create(
                CatalogueItem(
                    item_id=None,
                    kind=CatalogueKind.PRODUCT,
                    name="Alpha",
                    is_active=True,
                )
            )
            repo.create(
                CatalogueItem(
                    item_id=None,
                    kind=CatalogueKind.PRODUCT,
                    name="Beta",
                    is_active=False,
                )
            )
            work.commit()

        with initialized_database.unit_of_work() as work:
            repo = CatalogueRepository(work.session)
            all_rows = repo.list(CatalogueKind.PRODUCT)
            active_only = repo.list(CatalogueKind.PRODUCT, include_inactive=False)
            search = repo.list(CatalogueKind.PRODUCT, search="alp")
            assert len(all_rows) == 2
            assert len(active_only) == 1
            assert active_only[0].name == "Alpha"
            assert len(search) == 1


class TestCatalogueService:
    def test_create_product_and_service(self, initialized_database, auth_services):
        _owner(auth_services)
        service = CatalogueService(_runtime(initialized_database), auth_services=auth_services)

        product = service.save_item(
            CatalogueItem(
                item_id=None,
                kind=CatalogueKind.PRODUCT,
                name="Flex Banner",
                unit="sq ft",
                default_sale_price_minor=2500,
                description="Outdoor banner",
            )
        )
        assert product.success
        assert product.item is not None
        assert product.item.kind == CatalogueKind.PRODUCT

        svc = service.save_item(
            CatalogueItem(
                item_id=None,
                kind=CatalogueKind.SERVICE,
                name="Design Service",
                unit="hour",
                default_sale_price_minor=10000,
            )
        )
        assert svc.success
        assert svc.item is not None
        assert svc.item.kind == CatalogueKind.SERVICE

    def test_duplicate_warn_and_confirm(self, initialized_database, auth_services):
        _owner(auth_services)
        service = CatalogueService(_runtime(initialized_database), auth_services=auth_services)

        first = service.save_item(
            CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name="Card")
        )
        assert first.success

        warned = service.save_item(
            CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name=" card ")
        )
        assert not warned.success
        assert warned.warnings
        assert "Possible duplicate" in warned.message or warned.warnings

        confirmed = service.save_item(
            CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name=" card "),
            confirm_duplicates=True,
        )
        assert confirmed.success
        assert confirmed.item is not None

    def test_edit_and_activation_audit(self, initialized_database, auth_services):
        _owner(auth_services)
        service = CatalogueService(_runtime(initialized_database), auth_services=auth_services)

        created = service.save_item(
            CatalogueItem(
                item_id=None,
                kind=CatalogueKind.SERVICE,
                name="Print",
                is_active=True,
            )
        )
        assert created.success and created.item is not None

        updated = service.save_item(
            CatalogueItem(
                item_id=created.item.item_id,
                kind=CatalogueKind.SERVICE,
                name="Print Updated",
                is_active=False,
            ),
            confirm_duplicates=True,
        )
        assert updated.success
        assert updated.item is not None
        assert updated.item.is_active is False

        events = _audit_events(initialized_database)
        types = [e.event_type for e in events]
        assert "catalogue.created" in types
        assert "catalogue.updated" in types
        assert "catalogue.deactivated" in types

    def test_set_active(self, initialized_database, auth_services):
        _owner(auth_services)
        service = CatalogueService(_runtime(initialized_database), auth_services=auth_services)
        created = service.save_item(
            CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name="A", is_active=True)
        )
        assert created.item is not None and created.item.item_id is not None
        pid = created.item.item_id

        deactivated = service.set_active(pid, active=False)
        assert deactivated.success and deactivated.item is not None
        assert not deactivated.item.is_active

        activated = service.set_active(pid, active=True)
        assert activated.success and activated.item is not None
        assert activated.item.is_active

    def test_role_authorization(self, initialized_database, auth_services):
        _owner(auth_services)
        _add_user(auth_services, "operator", RoleKey.OPERATOR)
        _add_user(auth_services, "acctrev", RoleKey.ACCOUNTANT_REVIEWER)
        _add_user(auth_services, "viewer1", RoleKey.VIEWER)

        service = CatalogueService(_runtime(initialized_database), auth_services=auth_services)

        _login(auth_services, "operator")
        op = service.save_item(
            CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name="OpProd")
        )
        assert op.success

        _login(auth_services, "acctrev")
        with pytest.raises(AuthorizationError):
            service.save_item(CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name="Nope"))
        rows = service.list_items(CatalogueKind.PRODUCT)
        assert any(p.name == "OpProd" for p in rows)

        _login(auth_services, "viewer1")
        with pytest.raises(AuthorizationError):
            service.save_item(CatalogueItem(item_id=None, kind=CatalogueKind.PRODUCT, name="Nope2"))
        rows = service.list_items(CatalogueKind.PRODUCT)
        assert len(rows) >= 1

    def test_no_hard_delete_api(self):
        assert not hasattr(CatalogueService, "delete")
        assert not hasattr(CatalogueService, "delete_item")


class TestCatalogueMigration:
    def test_catalogue_table_exists(self, initialized_database):
        with initialized_database.engine.connect() as conn:
            rows = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='catalogue_items'"
            ).fetchall()
        assert len(rows) == 1

    def test_upgrade_preserves_existing_data(self, initialized_database):
        # Downgrade to 0005, insert party data, upgrade to head, verify preserved.
        manager = MigrationManager(initialized_database)
        manager.downgrade("0005_party_master")
        with initialized_database.unit_of_work() as work:
            from app.domain.party import Party, PartyKind
            from app.infrastructure.database.party_repository import PartyRepository

            PartyRepository(work.session).create(
                Party(party_id=None, kind=PartyKind.CUSTOMER, name="Preserved")
            )
            work.commit()

        manager.upgrade()
        with initialized_database.unit_of_work() as work:
            from app.domain.party import PartyKind
            from app.infrastructure.database.party_repository import PartyRepository

            parties = PartyRepository(work.session).list(PartyKind.CUSTOMER)
            assert any(p.name == "Preserved" for p in parties)

        with initialized_database.engine.connect() as conn:
            rows = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='catalogue_items'"
            ).fetchall()
        assert len(rows) == 1
