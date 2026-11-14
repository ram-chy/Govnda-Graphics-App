"""Database location rules: absolute paths, no implicit creation, no defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import DatabaseUnavailableError
from app.infrastructure.database.config import DatabaseConfig


def test_path_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="absolute"):
        DatabaseConfig(path=Path("relative") / "test.db")


def test_path_must_name_a_file() -> None:
    with pytest.raises(ValueError, match="name a database file"):
        DatabaseConfig(path=Path(Path.cwd().anchor))


def test_busy_timeout_must_be_a_positive_integer() -> None:
    path = Path.cwd().resolve() / "x.db"
    for value in (0, -1, 600_001, True, 1.5):
        with pytest.raises(ValueError, match="busy_timeout_ms"):
            DatabaseConfig(path=path, busy_timeout_ms=value)  # type: ignore[arg-type]


def test_url_contains_the_absolute_path(database_config: DatabaseConfig) -> None:
    url = database_config.url

    assert url.get_backend_name() == "sqlite"
    assert url.database == str(database_config.path)
    assert Path(url.database or "").is_absolute()


def test_wal_and_shm_paths_are_derived_from_the_database_file(
    database_config: DatabaseConfig,
) -> None:
    assert database_config.wal_path == database_config.path.with_name("test.db-wal")
    assert database_config.shm_path == database_config.path.with_name("test.db-shm")


def test_missing_parent_is_an_error_and_is_not_created(tmp_path: Path) -> None:
    missing_parent = tmp_path / "missing"
    config = DatabaseConfig(path=missing_parent / "test.db")

    with pytest.raises(DatabaseUnavailableError):
        config.validate_parent()
    assert not missing_parent.exists()


def test_validate_parent_accepts_an_existing_folder(database_config: DatabaseConfig) -> None:
    database_config.validate_parent()


def test_writability_probe_leaves_no_files(database_config: DatabaseConfig) -> None:
    before = set(database_config.parent.iterdir())

    database_config.verify_writable_parent()

    assert set(database_config.parent.iterdir()) == before


def test_require_absent_file_never_deletes_an_existing_database(
    database_config: DatabaseConfig,
) -> None:
    database_config.path.write_bytes(b"existing database")

    with pytest.raises(DatabaseUnavailableError, match="already exists"):
        database_config.require_absent_file()
    assert database_config.path.read_bytes() == b"existing database"


def test_require_existing_file_does_not_create_a_missing_database(
    database_config: DatabaseConfig,
) -> None:
    with pytest.raises(DatabaseUnavailableError, match="does not exist"):
        database_config.require_existing_file()
    assert not database_config.path.exists()


def test_require_existing_file_rejects_a_directory(database_config: DatabaseConfig) -> None:
    database_config.path.mkdir()

    with pytest.raises(DatabaseUnavailableError):
        database_config.require_existing_file()
