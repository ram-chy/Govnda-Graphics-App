"""Alembic control, startup policy, and baseline database identity."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, UniqueConstraint, text

from app.core.exceptions import DatabaseUnavailableError, MigrationError
from app.infrastructure.database.base import APPLICATION_ID, NAMING_CONVENTION, SCHEMA_USER_VERSION
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import (
    MigrationManager,
    MigrationState,
    application_head_revision,
    default_migrations_dir,
    evaluate_migration_state,
    read_application_id,
    verify_database_for_startup,
)

HEAD_REVISION = application_head_revision()


def _pragma(database: Database, statement: str) -> object:
    with database.engine.connect() as connection:
        return connection.exec_driver_sql(statement).scalar()


def _table_names(database: Database) -> set[str]:
    with database.engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_evaluate_migration_state_policy() -> None:
    known = {"0001_baseline"}

    assert (
        evaluate_migration_state("0001_baseline", "0001_baseline", known)
        is MigrationState.UP_TO_DATE
    )
    assert evaluate_migration_state(None, "0001_baseline", known) is MigrationState.NOT_INITIALIZED
    assert (
        evaluate_migration_state("0000_old", "0001_baseline", known)
        is MigrationState.NEWER_SCHEMA
    )

    newer_known = {"0000_old", "0001_baseline"}
    assert (
        evaluate_migration_state("0000_old", "0001_baseline", newer_known)
        is MigrationState.UPGRADE_REQUIRED
    )


def test_evaluate_migration_state_requires_a_head() -> None:
    with pytest.raises(MigrationError):
        evaluate_migration_state(None, None, set())


def test_default_migrations_directory_contains_the_baseline() -> None:
    directory = default_migrations_dir()

    assert directory.is_dir()
    assert (directory / "versions" / "0001_baseline.py").is_file()
    assert (directory / "versions" / "0002_business_profile.py").is_file()
    assert (directory / "versions" / "0003_business_profile_requirements.py").is_file()


def test_create_database_applies_the_baseline_identity(
    initialized_database: Database,
) -> None:
    assert read_application_id(initialized_database) == APPLICATION_ID
    assert _pragma(initialized_database, "PRAGMA user_version") == SCHEMA_USER_VERSION
    assert int(_pragma(initialized_database, "PRAGMA application_id") or 0) == 0x47424753


def test_migrations_create_the_business_profile_table(initialized_database: Database) -> None:
    assert _table_names(initialized_database) == {
        "alembic_version",
        "business_profile",
        "business_profile_versions",
        "audit_events",
    }


def test_status_reports_up_to_date(initialized_database: Database) -> None:
    status = MigrationManager(initialized_database).status()

    assert status.state is MigrationState.UP_TO_DATE
    assert status.current_revision == HEAD_REVISION
    assert status.head_revision == HEAD_REVISION
    assert status.pending_revisions == ()
    assert status.is_up_to_date


def test_history_lists_the_approved_revisions(initialized_database: Database) -> None:
    entries = MigrationManager(initialized_database).history()
    revisions = {entry.revision: entry.down_revision for entry in entries}

    assert set(revisions) == {
        "0001_baseline",
        "0002_business_profile",
        "0003_business_profile_requirements",
    }
    assert revisions["0001_baseline"] is None
    assert revisions["0002_business_profile"] == "0001_baseline"
    assert revisions["0003_business_profile_requirements"] == "0002_business_profile"


def test_create_database_refuses_an_existing_file(database_config: DatabaseConfig) -> None:
    database_config.path.write_bytes(b"keep me")
    database = Database(database_config)
    try:
        with pytest.raises(DatabaseUnavailableError, match="already exists"):
            MigrationManager(database).create_database()
        assert database_config.path.read_bytes() == b"keep me"
    finally:
        database.shutdown()


def test_create_database_refuses_a_missing_parent(tmp_path: Path) -> None:
    config = DatabaseConfig(path=tmp_path / "missing" / "test.db")
    database = Database(config)
    try:
        with pytest.raises(DatabaseUnavailableError):
            MigrationManager(database).create_database()
        assert not config.parent.exists()
    finally:
        database.shutdown()


def test_upgrade_never_creates_a_missing_database(database_config: DatabaseConfig) -> None:
    database = Database(database_config)
    try:
        with pytest.raises(DatabaseUnavailableError, match="does not exist"):
            MigrationManager(database).upgrade()
        assert not database_config.path.exists()
    finally:
        database.shutdown()


def test_upgrade_from_an_uninitialized_file_applies_the_baseline(
    database_config: DatabaseConfig,
) -> None:
    database_config.path.write_bytes(b"")
    database = Database(database_config)
    try:
        manager = MigrationManager(database)
        assert manager.status().state is MigrationState.NOT_INITIALIZED

        status = manager.upgrade()

        assert status.is_up_to_date
        assert status.current_revision == HEAD_REVISION
        assert read_application_id(database) == APPLICATION_ID
    finally:
        database.shutdown()


def test_failed_upgrade_leaves_the_database_unchanged(
    initialized_database: Database,
) -> None:
    manager = MigrationManager(initialized_database)
    before = manager.status()
    application_id = read_application_id(initialized_database)

    with pytest.raises(MigrationError):
        manager.upgrade("9999_missing_revision")

    after = manager.status()
    assert after == before
    assert after.current_revision == HEAD_REVISION
    assert read_application_id(initialized_database) == application_id


def test_naming_convention_produces_stable_constraint_names() -> None:
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    table = Table(
        "example",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("email", String(120), unique=True, nullable=False),
    )

    assert table.primary_key.name == "pk_example"
    unique_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_names == {"uq_example_email"}


def test_downgrade_to_base_removes_the_revision_and_identity(
    initialized_database: Database,
) -> None:
    manager = MigrationManager(initialized_database)

    status = manager.downgrade("base")

    assert status.state is MigrationState.NOT_INITIALIZED
    assert status.current_revision is None
    assert read_application_id(initialized_database) == 0
    assert _pragma(initialized_database, "PRAGMA user_version") == 0
    with initialized_database.engine.connect() as connection:
        remaining = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM alembic_version"
        ).scalar_one()
    assert remaining == 0


def test_uninitialized_file_requires_migration(database_config: DatabaseConfig) -> None:
    database_config.path.write_bytes(b"")
    database = Database(database_config)
    try:
        status = MigrationManager(database).status()
        assert status.state is MigrationState.NOT_INITIALIZED
        with pytest.raises(MigrationError, match="requires migration"):
            verify_database_for_startup(database)
    finally:
        database.shutdown()


def test_newer_schema_is_refused_at_startup(initialized_database: Database) -> None:
    with initialized_database.engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = '9999_future'"))

    status = MigrationManager(initialized_database).status()
    assert status.state is MigrationState.NEWER_SCHEMA
    with pytest.raises(MigrationError, match="not known"):
        verify_database_for_startup(initialized_database)


def test_wrong_application_id_is_refused_at_startup(database_config: DatabaseConfig) -> None:
    with sqlite3.connect(database_config.path) as connection:
        connection.execute("PRAGMA application_id = 12345")
    database = Database(database_config)
    try:
        with pytest.raises(DatabaseUnavailableError, match="unexpected application_id") as excinfo:
            verify_database_for_startup(database)
        assert "not a Gobindas" in excinfo.value.user_message
    finally:
        database.shutdown()


def test_startup_verification_accepts_the_current_schema(initialized_database: Database) -> None:
    status = verify_database_for_startup(initialized_database)

    assert status.is_up_to_date
    assert status.current_revision == HEAD_REVISION


def test_startup_verification_does_not_upgrade(initialized_database: Database) -> None:
    """A foreign/incomplete schema must be reported, never silently migrated."""
    with initialized_database.engine.begin() as connection:
        connection.execute(text("DELETE FROM alembic_version"))

    with pytest.raises(MigrationError):
        verify_database_for_startup(initialized_database)

    with initialized_database.engine.connect() as connection:
        remaining = connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one()
    assert remaining == 0
