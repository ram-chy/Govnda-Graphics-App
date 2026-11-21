"""Business Profile service transactions, logo storage, history, and audit."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import AppConfig
from app.domain.audit import PROFILE_ENTITY_TYPE, UNAUTHENTICATED_ACTOR, ProfileAuditEventType
from app.domain.business_profile import BusinessProfile, ProfileStatus
from app.infrastructure.database.business_profile_repository import BusinessProfileRepository
from app.infrastructure.database.engine import Database
from app.infrastructure.filesystem.layout import DataRootLayout
from app.services.business_profile_service import (
    BusinessProfileService,
    BusinessProfileServiceFactory,
)
from app.services.database_runtime import DatabaseRuntime
from app.services.logo_storage_service import LogoStorageService


def clock() -> str:
    return "2026-11-20T10:30:00Z"


def _service(database: Database, data_root: Path) -> BusinessProfileService:
    storage = LogoStorageService(DataRootLayout(data_root), clock=clock)
    return BusinessProfileService(database, storage, clock=clock)


def _complete_profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Gobindas Graphics",
        address="Sector 1",
        phone="9876543210",
        email="office@example.com",
        footer_message="Thank you",
    )


def _counts(database: Database) -> tuple[int, int, int]:
    with database.engine.connect() as connection:
        profile = connection.exec_driver_sql("SELECT COUNT(*) FROM business_profile").scalar_one()
        versions = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM business_profile_versions"
        ).scalar_one()
        audit = connection.exec_driver_sql("SELECT COUNT(*) FROM audit_events").scalar_one()
    return int(profile), int(versions), int(audit)


def test_load_reports_an_empty_profile(
    initialized_database: Database, profile_data_root: Path
) -> None:
    result = _service(initialized_database, profile_data_root).load()

    assert result.profile is None
    assert result.completion.status is ProfileStatus.EMPTY
    assert result.versions == ()


def test_save_persists_normalized_values_history_and_audit(
    initialized_database: Database, profile_data_root: Path, logo_file: Path
) -> None:
    service = _service(initialized_database, profile_data_root)
    draft = BusinessProfile(
        business_name="  Gobindas Graphics  ",
        address="  Sector 1  ",
        phone=" 9876543210 ",
        email=" office@example.com ",
        footer_message="  Thank you  ",
        website=" example.com ",
    )

    result = service.save(draft, logo_path=logo_file)

    assert result.success
    assert result.message == "Business profile saved."
    assert result.profile is not None
    assert result.profile.business_name == "Gobindas Graphics"
    assert result.profile.address == "Sector 1"
    assert result.profile.website == "example.com"
    assert result.profile.logo_reference.startswith("Logos/")
    assert result.profile.version_number == 1
    assert result.completion.status is ProfileStatus.COMPLETE

    reloaded = service.load()
    assert reloaded.profile == result.profile
    assert len(reloaded.versions) == 1
    assert reloaded.versions[0].business_name == "Gobindas Graphics"
    assert reloaded.logo_preview_path is not None
    assert reloaded.logo_preview_path.is_file()
    assert _counts(initialized_database) == (1, 1, 2)
    events = service.audit_events()
    assert {event.event_type for event in events} == {
        "business_profile.created",
        "business_profile.logo_changed",
    }
    assert all(event.actor == UNAUTHENTICATED_ACTOR for event in events)


def test_update_creates_a_new_immutable_version(
    initialized_database: Database, profile_data_root: Path, logo_file: Path
) -> None:
    service = _service(initialized_database, profile_data_root)
    assert service.save(_complete_profile(), logo_path=logo_file).success

    updated = replace(_complete_profile(), business_name="New Name")
    result = service.save(updated)

    assert result.success
    assert result.profile is not None
    assert result.profile.version_number == 2
    assert len(service.history()) == 2
    assert [version.version_number for version in service.history()] == [1, 2]
    assert service.history()[0].business_name == "Gobindas Graphics"
    assert service.history()[1].business_name == "New Name"
    assert "business_profile.updated" in {
        event.event_type for event in service.audit_events()
    }


def test_invalid_save_does_not_persist_anything(
    initialized_database: Database, profile_data_root: Path
) -> None:
    service = _service(initialized_database, profile_data_root)

    result = service.save(BusinessProfile(address="Address without required fields"))

    assert not result.success
    assert result.profile is None
    assert result.field_errors == {
        "business_name": "Business name is required.",
        "phone": "Phone is required.",
        "email": "Email is required.",
        "footer_message": "Footer message is required.",
        "logo": "A business logo is required.",
    }
    assert _counts(initialized_database) == (0, 0, 0)
    assert service.audit_events() == ()


def test_history_view_records_an_audit_event(
    initialized_database: Database, profile_data_root: Path, logo_file: Path
) -> None:
    service = _service(initialized_database, profile_data_root)
    assert service.save(_complete_profile(), logo_path=logo_file).success
    before = len(service.audit_events())

    service.record_history_viewed(1)

    events = service.audit_events()
    assert len(events) == before + 1
    event = events[-1]
    assert event.event_type == ProfileAuditEventType.HISTORY_VIEWED
    assert event.entity_type == PROFILE_ENTITY_TYPE
    assert event.entity_id == "1"
    assert event.actor == UNAUTHENTICATED_ACTOR
    assert event.payload == '{"version":1}'


def test_invalid_logo_preserves_the_current_logo_reference(
    initialized_database: Database, profile_data_root: Path, logo_file: Path, tmp_path
) -> None:
    service = _service(initialized_database, profile_data_root)
    assert service.save(_complete_profile(), logo_path=logo_file).success
    original = service.load().profile
    assert original is not None
    bad_logo = tmp_path / "not-a-logo.png"
    bad_logo.write_bytes(b"definitely not a png")

    result = service.save(_complete_profile(), logo_path=bad_logo)

    assert not result.success
    assert "PNG" in result.message
    current = service.load().profile
    assert current is not None
    assert current.logo_reference == original.logo_reference
    assert Path(profile_data_root / current.logo_reference).is_file()
    assert len(service.history()) == 1


def test_upsert_never_creates_a_second_profile(
    initialized_database: Database, profile_data_root: Path, logo_file: Path
) -> None:
    service = _service(initialized_database, profile_data_root)
    assert service.save(_complete_profile(), logo_path=logo_file).success
    second = replace(_complete_profile(), business_name="Second")
    assert service.save(second).success

    reloaded = service.load()
    assert reloaded.profile is not None
    assert reloaded.profile.business_name == "Second"
    with initialized_database.engine.connect() as connection:
        count = connection.exec_driver_sql("SELECT COUNT(*) FROM business_profile").scalar_one()
    assert count == 1


def test_storage_failure_rolls_back_and_reports_a_reference(
    initialized_database: Database,
    profile_data_root: Path,
    logo_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(initialized_database, profile_data_root)
    assert service.save(_complete_profile(), logo_path=logo_file).success
    original = service.load().profile
    logo_files_before = set((profile_data_root / "Logos").iterdir())

    def fail_after_mutating(self: BusinessProfileRepository, profile: object) -> None:
        record = self.load()
        assert record is not None
        record.business_name = "Corrupted by failed save"
        raise SQLAlchemyError("simulated storage failure")

    monkeypatch.setattr(BusinessProfileRepository, "save", fail_after_mutating)
    replacement = replace(_complete_profile(), business_name="Replacement")
    bad_logo = logo_file.parent / "replacement.png"
    bad_logo.write_bytes(logo_file.read_bytes())
    result = service.save(replacement, logo_path=bad_logo)

    assert not result.success
    assert result.field_errors == {}
    assert "Reference:" in result.message
    reloaded = service.load()
    assert reloaded.profile == original
    assert set((profile_data_root / "Logos").iterdir()) == logo_files_before
    assert len(service.history()) == 1
    assert len(service.audit_events()) == 2


def test_immutable_version_rows_reject_update_and_delete(initialized_database: Database) -> None:
    with initialized_database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO business_profile "
                "(id, business_name, created_at, updated_at) "
                "VALUES (1, 'Name', 'now', 'now')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO business_profile_versions "
                "(profile_id, version_number, business_name, address, phone, secondary_phone, "
                "email, website, registration_number, footer_message, logo_reference, "
                "created_at, updated_at) "
                "VALUES (1, 1, 'Name', '', '', '', '', '', '', '', '', 'now', 'now')"
            )
        )
    with pytest.raises(IntegrityError), initialized_database.engine.begin() as connection:
        connection.execute(
            text("UPDATE business_profile_versions SET business_name = 'Changed'")
        )
    with pytest.raises(IntegrityError), initialized_database.engine.begin() as connection:
        connection.execute(text("DELETE FROM business_profile_versions"))


def test_factory_follows_the_current_database_and_data_root(
    initialized_database: Database,
    profile_data_root: Path,
    config_service,
) -> None:
    config = AppConfig().with_database_location(
        data_root=profile_data_root, database_path=initialized_database.config.path
    )
    config_service.save(config)
    runtime = DatabaseRuntime()
    factory = BusinessProfileServiceFactory(config_service, runtime)

    assert factory.build() is None
    runtime.install(initialized_database)
    service = factory.build()
    assert service is not None
    assert isinstance(service, BusinessProfileService)
    assert service.load().profile is None


def test_persistence_error_type_is_logged_without_profile_values(
    initialized_database: Database,
    profile_data_root: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _service(initialized_database, profile_data_root)

    with patch.object(
        BusinessProfileRepository,
        "save",
        side_effect=SQLAlchemyError("secret profile value must not be logged"),
    ):
        result = service.save(
            replace(_complete_profile(), logo_reference="Logos/logo.png")
        )

    assert not result.success
    assert "Secret Business" not in caplog.text
    assert "Gobindas Graphics" not in caplog.text
    assert "secret profile value must not be logged" not in caplog.text
    assert "SQLAlchemyError" in caplog.text
