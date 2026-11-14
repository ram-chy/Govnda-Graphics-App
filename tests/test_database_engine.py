"""Engine PRAGMA profile, database lifecycle, and no-implicit-creation rules."""

from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DatabaseUnavailableError
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database, create_sqlite_engine
from app.infrastructure.database.migrations import MigrationManager


def _pragma(database: Database, statement: str) -> object:
    with database.engine.connect() as connection:
        return connection.exec_driver_sql(statement).scalar()


def test_engine_applies_the_approved_pragma_profile(
    initialized_database: Database,
) -> None:
    assert _pragma(initialized_database, "PRAGMA foreign_keys") == 1
    assert str(_pragma(initialized_database, "PRAGMA journal_mode")).lower() == "wal"
    assert _pragma(initialized_database, "PRAGMA busy_timeout") == 5_000
    assert _pragma(initialized_database, "PRAGMA synchronous") == 2  # FULL
    assert _pragma(initialized_database, "PRAGMA wal_autocheckpoint") == 1_000
    assert _pragma(initialized_database, "PRAGMA temp_store") == 2  # MEMORY
    assert _pragma(initialized_database, "PRAGMA trusted_schema") == 0


def test_busy_timeout_is_configurable(db_dir) -> None:
    config = DatabaseConfig(path=db_dir / "timeout.db", busy_timeout_ms=1_250)
    database = Database(config)
    try:
        MigrationManager(database).create_database()
        assert _pragma(database, "PRAGMA busy_timeout") == 1_250
    finally:
        database.shutdown()


def test_engine_exposes_the_sqlite_version(initialized_database: Database) -> None:
    version = initialized_database.sqlite_version()

    assert version == sqlite3.sqlite_version


def test_verify_accessible_does_not_create_a_missing_database(
    database_config: DatabaseConfig,
) -> None:
    database = Database(database_config)
    try:
        with pytest.raises(DatabaseUnavailableError, match="does not exist"):
            database.verify_accessible()
        assert not database_config.path.exists()
    finally:
        database.shutdown()


def test_shutdown_is_idempotent(initialized_database: Database) -> None:
    initialized_database.shutdown()
    initialized_database.shutdown()


def test_database_context_manager_disposes_on_exit(database_config: DatabaseConfig) -> None:
    with Database(database_config) as database:
        MigrationManager(database).create_database()

    assert database_config.path.exists()


def test_session_writes_are_visible_after_commit(initialized_database: Database) -> None:
    with initialized_database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE scratch (value INTEGER)"))
    with initialized_database.engine.begin() as connection:
        connection.execute(text("INSERT INTO scratch (value) VALUES (42)"))

    with initialized_database.engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM scratch")).scalar_one() == 42


def test_foreign_key_violation_is_rejected(initialized_database: Database) -> None:
    with initialized_database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE child ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER NOT NULL REFERENCES parent(id)"
                ")"
            )
        )

    with pytest.raises(IntegrityError), initialized_database.engine.begin() as connection:
        connection.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 99)"))

    with initialized_database.engine.begin() as connection:
        connection.execute(text("INSERT INTO parent (id) VALUES (99)"))
        connection.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 99)"))


def test_create_sqlite_engine_uses_a_bounded_pool(database_config: DatabaseConfig) -> None:
    engine = create_sqlite_engine(database_config)
    try:
        assert engine.pool.size() == 2
        assert engine.pool._max_overflow == 0  # noqa: SLF001 - verifies the documented policy
    finally:
        engine.dispose()
