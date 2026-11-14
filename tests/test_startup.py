"""End-to-end startup tests for the real entry point.

The application is started in a subprocess with isolated APPDATA and
LOCALAPPDATA folders and the offscreen Qt platform.
"""

from __future__ import annotations

import json
import os
import sqlite3
import string
import subprocess
import sys
import uuid
from pathlib import Path

from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_config(
    tmp_path: Path,
    database_path: Path | None,
    *,
    data_root: Path | None = None,
) -> None:
    config_dir = tmp_path / "Roaming" / "GobindasBMS"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1}
    if data_root is not None:
        payload["data_root"] = str(data_root)
    if database_path is not None:
        payload["database_path"] = str(database_path)
    (config_dir / "config.json").write_text(json.dumps(payload), encoding="utf-8")


def _create_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(DatabaseConfig(path=path))
    try:
        MigrationManager(database).create_database()
    finally:
        database.shutdown()


def _log_text(tmp_path: Path) -> str:
    return (tmp_path / "Local" / "GobindasBMS" / "logs" / "app.log").read_text(
        encoding="utf-8"
    )


def _isolated_env(tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["APPDATA"] = str(tmp_path / "Roaming")
    environment["LOCALAPPDATA"] = str(tmp_path / "Local")
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    # Each test gets its own mutex so a running application (or another test)
    # cannot make startup fail for an unrelated reason.
    environment["GOBINDAS_MUTEX_NAME"] = rf"Local\GGBMS.Test.{uuid.uuid4().hex}"
    return environment


def _run_smoke(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.main", "--smoke-test"],
        cwd=PROJECT_ROOT,
        env=_isolated_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _missing_drive() -> str:
    """Return a drive letter that does not exist on this machine."""
    for letter in reversed(string.ascii_uppercase):
        candidate = f"{letter}:\\"
        if not Path(candidate).exists():
            return candidate
    raise AssertionError("every drive letter is in use on this machine")


def test_first_launch_without_configuration_requires_setup(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    content = _log_text(tmp_path)
    assert "Setup required" in content
    assert "Smoke test exiting without opening a window" in content
    assert "Main window shown" not in content
    assert "Traceback" not in content
    assert "CRITICAL" not in content
    assert not (tmp_path / "Roaming" / "GobindasBMS" / "config.json").exists()


def test_first_launch_creates_no_database_or_configuration(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    database_files = [
        path
        for path in tmp_path.rglob("*")
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm"}
    ]
    assert database_files == []
    assert not (tmp_path / "Roaming" / "GobindasBMS" / "config.json").exists()


def test_corrupt_configuration_requires_recovery_and_is_preserved(tmp_path: Path) -> None:
    config_dir = tmp_path / "Roaming" / "GobindasBMS"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text("{ this is not json", encoding="utf-8")

    result = _run_smoke(tmp_path)

    assert result.returncode == 1
    content = _log_text(tmp_path)
    assert "Configuration file is invalid" in content
    assert "Invalid configuration preserved" in content
    assert "recovery required" in content.lower()
    assert "Main window shown" not in content
    quarantined = list(config_dir.glob("config.corrupt-*.json"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == "{ this is not json"
    # A corrupt settings file is never silently replaced by a default file.
    assert not (config_dir / "config.json").exists()


def test_configured_database_opens_and_logs_location(tmp_path: Path) -> None:
    data_root = tmp_path / "business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    _write_config(tmp_path, database_path, data_root=data_root)

    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    content = _log_text(tmp_path)
    assert "Database ready" in content
    assert "schema=0001_baseline" in content
    assert f"data root={data_root}" in content
    assert "Main window shown" in content
    assert "ERROR" not in content


def test_legacy_configuration_without_data_root_still_opens(tmp_path: Path) -> None:
    database_path = tmp_path / "business" / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    _write_config(tmp_path, database_path)

    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    content = _log_text(tmp_path)
    assert "Database ready" in content
    assert "legacy configuration" in content
    assert "Main window shown" in content


def test_missing_configured_database_blocks_without_creating_it(tmp_path: Path) -> None:
    data_root = tmp_path / "business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    (data_root / "Database").mkdir(parents=True)
    _write_config(tmp_path, database_path, data_root=data_root)

    result = _run_smoke(tmp_path)

    assert result.returncode == 1
    assert not database_path.exists()
    content = _log_text(tmp_path)
    assert "does not exist" in content
    assert "Main window shown" not in content


def test_missing_drive_blocks_without_a_fallback_database(tmp_path: Path) -> None:
    data_root = Path(_missing_drive()) / "GobindasBusiness"
    database_path = data_root / "Database" / "BusinessManagement.db"
    _write_config(tmp_path, database_path, data_root=data_root)

    result = _run_smoke(tmp_path)

    assert result.returncode == 1
    content = _log_text(tmp_path)
    assert "not available" in content
    assert "Main window shown" not in content
    assert not database_path.exists()
    # No application database may be created anywhere under the isolated profile.
    created = [
        path
        for path in tmp_path.rglob("*")
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
    ]
    assert created == []


def test_startup_refuses_a_newer_schema_and_does_not_migrate(tmp_path: Path) -> None:
    data_root = tmp_path / "business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    _create_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE alembic_version SET version_num = '9999_future'")
    _write_config(tmp_path, database_path, data_root=data_root)

    result = _run_smoke(tmp_path)

    assert result.returncode == 1
    content = _log_text(tmp_path)
    assert "newer than this application understands" in content
    assert "Main window shown" not in content
    with sqlite3.connect(database_path) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert revision == ("9999_future",)


def test_startup_refuses_an_uninitialized_database_and_does_not_upgrade(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    database_path.write_bytes(b"")
    _write_config(tmp_path, database_path, data_root=data_root)

    result = _run_smoke(tmp_path)

    assert result.returncode == 1
    content = _log_text(tmp_path)
    assert "must be migrated" in content
    assert "Main window shown" not in content
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert "alembic_version" not in tables


def test_startup_refuses_a_corrupt_database_without_modifying_it(tmp_path: Path) -> None:
    data_root = tmp_path / "business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    original = b"this is not a sqlite database" * 128
    database_path.write_bytes(original)
    _write_config(tmp_path, database_path, data_root=data_root)

    result = _run_smoke(tmp_path)

    assert result.returncode == 1
    assert database_path.read_bytes() == original
    content = _log_text(tmp_path)
    assert "Main window shown" not in content
