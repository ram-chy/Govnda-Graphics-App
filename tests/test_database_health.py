"""Read-only health diagnostics, including corruption and identity reporting."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import DatabaseDiagnostics, DatabaseHealthStatus


def _database(path: Path) -> Database:
    return Database(DatabaseConfig(path=path))


def test_healthy_database(initialized_database: Database) -> None:
    report = DatabaseDiagnostics(initialized_database).check()

    assert report.status is DatabaseHealthStatus.HEALTHY
    assert report.healthy
    assert report.sqlite_version
    assert report.application_id == 0x47424753
    assert report.user_version == 1
    assert report.migration is not None
    assert report.migration.is_up_to_date
    assert report.file_info is not None
    assert report.file_info.exists
    assert report.file_info.size_bytes and report.file_info.size_bytes > 0


def test_full_check_passes_on_a_healthy_database(initialized_database: Database) -> None:
    report = DatabaseDiagnostics(initialized_database).check(full=True)

    assert report.status is DatabaseHealthStatus.HEALTHY
    assert report.checks["integrity_check"] == "ok"


def test_missing_database_is_reported_without_creating_it(
    database_config: DatabaseConfig,
) -> None:
    database = _database(database_config.path)
    try:
        report = DatabaseDiagnostics(database).check()
        assert report.status is DatabaseHealthStatus.MISSING_DATABASE
        assert report.file_info is not None
        assert not report.file_info.exists
        assert not database_config.path.exists()
    finally:
        database.shutdown()


def test_missing_parent_folder_is_reported_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "test.db"
    database = _database(path)
    try:
        report = DatabaseDiagnostics(database).check()
        assert report.status is DatabaseHealthStatus.UNAVAILABLE_PATH
        assert not path.parent.exists()
    finally:
        database.shutdown()


def test_wrong_application_id_is_reported(database_config: DatabaseConfig) -> None:
    with sqlite3.connect(database_config.path) as connection:
        connection.execute("PRAGMA application_id = 99")
    database = _database(database_config.path)
    try:
        report = DatabaseDiagnostics(database).check()
        assert report.status is DatabaseHealthStatus.WRONG_DATABASE
        assert report.application_id == 99
    finally:
        database.shutdown()


def test_uninitialized_database_requires_migration(database_config: DatabaseConfig) -> None:
    database_config.path.write_bytes(b"")
    database = _database(database_config.path)
    try:
        report = DatabaseDiagnostics(database).check()
        assert report.status is DatabaseHealthStatus.MIGRATION_REQUIRED
        assert report.migration is not None
        assert not report.migration.is_up_to_date
    finally:
        database.shutdown()


def test_corrupt_file_is_reported(database_config: DatabaseConfig) -> None:
    database_config.path.write_bytes(b"this is definitely not a sqlite database" * 100)
    database = _database(database_config.path)
    try:
        report = DatabaseDiagnostics(database).check()
        assert report.status in (
            DatabaseHealthStatus.CORRUPT,
            DatabaseHealthStatus.UNKNOWN_ERROR,
        )
        assert not report.healthy
    finally:
        database.shutdown()


def test_health_check_never_modifies_the_database_file(
    initialized_database: Database,
) -> None:
    before = initialized_database.config.path.read_bytes()

    DatabaseDiagnostics(initialized_database).check(full=True)

    assert initialized_database.config.path.read_bytes() == before


def test_quick_check_result_reports_ok(initialized_database: Database) -> None:
    result = DatabaseDiagnostics(initialized_database).quick_check()

    assert result.ok
    assert result.summary == "ok"


def test_foreign_key_check_is_empty(initialized_database: Database) -> None:
    result = DatabaseDiagnostics(initialized_database).foreign_key_check()

    assert result.ok
    assert result.messages == ()


def test_lock_failure_is_reported_as_locked(initialized_database: Database) -> None:
    """A second connection holding an exclusive lock must not crash the report."""
    config = DatabaseConfig(path=initialized_database.config.path, busy_timeout_ms=100)
    database = Database(config)
    blocking = sqlite3.connect(config.path, timeout=0)
    try:
        blocking.execute("BEGIN EXCLUSIVE")
        report = DatabaseDiagnostics(database).check()
    finally:
        blocking.rollback()
        blocking.close()
        database.shutdown()

    assert report.status in (
        DatabaseHealthStatus.LOCKED,
        DatabaseHealthStatus.PERMISSION_DENIED,
    )
    assert not report.healthy


def test_application_id_boundary_is_accepted(database_config: DatabaseConfig) -> None:
    with sqlite3.connect(database_config.path) as connection:
        connection.execute("PRAGMA application_id = 0")
    database = _database(database_config.path)
    try:
        report = DatabaseDiagnostics(database).check()
        # 0 means the file has not been initialized by this application yet.
        assert report.status is DatabaseHealthStatus.MIGRATION_REQUIRED
    finally:
        database.shutdown()


def test_other_application_id_is_rejected(database_config: DatabaseConfig) -> None:
    with sqlite3.connect(database_config.path) as connection:
        connection.execute("PRAGMA application_id = 1")
    database = _database(database_config.path)
    try:
        report = DatabaseDiagnostics(database).check()
        assert report.status is DatabaseHealthStatus.WRONG_DATABASE
    finally:
        database.shutdown()
