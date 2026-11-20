"""Migration coverage for the approved business-profile schema."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager


def _table_names(database: Database) -> set[str]:
    with database.engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_business_profile_table_has_only_approved_columns(initialized_database: Database) -> None:
    with initialized_database.engine.connect() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(business_profile)").fetchall()

    assert [str(row[1]) for row in rows] == [
        "id",
        "business_name",
        "address",
        "phone",
        "email",
        "website",
        "registration_number",
        "footer_message",
        "created_at",
        "updated_at",
        "secondary_phone",
        "logo_reference",
        "version_number",
    ]


def test_optional_columns_have_safe_empty_defaults(initialized_database: Database) -> None:
    with initialized_database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO business_profile "
                "(id, business_name, created_at, updated_at) "
                "VALUES (1, 'Gobindas Graphics', 'now', 'now')"
            )
        )
        row = connection.execute(
            text(
                "SELECT address, phone, email, website, registration_number, footer_message, "
                "secondary_phone, logo_reference, version_number FROM business_profile WHERE id = 1"
            )
        ).one()

    assert tuple(row) == ("", "", "", "", "", "", "", "", 0)


def test_history_and_audit_tables_exist(initialized_database: Database) -> None:
    names = _table_names(initialized_database)

    assert {"business_profile", "business_profile_versions", "audit_events"} <= names


def test_table_rejects_a_second_profile_row(initialized_database: Database) -> None:
    with initialized_database.engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO business_profile "
                "(id, business_name, created_at, updated_at) "
                "VALUES (2, 'Second', 'now', 'now')"
            )
        )


def test_migration_backfills_an_existing_profile_without_changing_its_values(
    initialized_database: Database,
) -> None:
    manager = MigrationManager(initialized_database)
    assert manager.downgrade("0002_business_profile").current_revision == (
        "0002_business_profile"
    )
    with initialized_database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO business_profile "
                "(id, business_name, address, phone, email, footer_message, "
                "created_at, updated_at) "
                "VALUES (1, 'Existing Business', 'Address', 'Phone', 'mail@example.com', "
                "'Footer', 'past', 'past')"
            )
        )

    manager.upgrade("0003_business_profile_requirements")

    with initialized_database.engine.connect() as connection:
        profile = connection.execute(
            text("SELECT business_name, version_number FROM business_profile WHERE id = 1")
        ).one()
        version = connection.execute(
            text(
                "SELECT version_number, business_name, footer_message "
                "FROM business_profile_versions"
            )
        ).one()
        audit = connection.execute(
            text("SELECT event_type, actor FROM audit_events")
        ).one()
    assert tuple(profile) == ("Existing Business", 1)
    assert tuple(version) == (1, "Existing Business", "Footer")
    assert tuple(audit) == ("business_profile.created", "system/unauthenticated")


def test_downgrade_removes_phase_7b_objects_then_the_profile_table(
    initialized_database: Database,
) -> None:
    manager = MigrationManager(initialized_database)

    status = manager.downgrade("0002_business_profile")

    assert status.current_revision == "0002_business_profile"
    assert "business_profile_versions" not in _table_names(initialized_database)
    assert "audit_events" not in _table_names(initialized_database)
    with initialized_database.engine.connect() as connection:
        columns = {
            str(row[1])
            for row in connection.exec_driver_sql("PRAGMA table_info(business_profile)").fetchall()
        }
    assert {"secondary_phone", "logo_reference", "version_number"}.isdisjoint(columns)

    status = manager.downgrade("0001_baseline")

    assert status.current_revision == "0001_baseline"
    assert "business_profile" not in _table_names(initialized_database)
