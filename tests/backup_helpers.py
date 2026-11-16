"""Shared builders for Phase 4 tests.

Every path is under pytest's ``tmp_path``. The real application data folder is
never touched, and no helper reads the user's configuration.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager
from app.infrastructure.filesystem.layout import DataRootLayout
from app.services.backup_service import BackupService
from app.services.backup_workspace import BackupWorkspaceFactory
from app.services.database_runtime import DatabaseRuntime


def create_database_at(path: Path) -> Path:
    """Create an initialized database at ``path`` and close the engine."""
    path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(DatabaseConfig(path=path))
    try:
        MigrationManager(database).create_database()
    finally:
        database.shutdown()
    return path


def create_data_root(tmp_path: Path, name: str = "Business") -> tuple[Path, Path]:
    """Return an approved-layout data root and its initialized database."""
    root = tmp_path / name
    database_path = DataRootLayout(root).database_path
    create_database_at(database_path)
    return root, database_path


def save_location(
    config_service: ConfigService,
    root: Path,
    database_path: Path,
    **overrides: object,
) -> AppConfig:
    config = AppConfig(
        theme="light",
        data_root=str(root),
        database_path=str(database_path),
        **overrides,
    )
    config_service.save(config)
    return config


def build_directories(root: Path) -> BackupDirectories:
    return BackupDirectories.from_layout(DataRootLayout(root))


def build_backup_service(
    root: Path,
    database_path: Path,
    *,
    clock=None,
    **kwargs: object,
) -> BackupService:
    directories = build_directories(root)
    return BackupService(
        directories=directories,
        database_path=database_path,
        lock=OperationLock(directories.lock_path, operation="backup"),
        state_store=BackupStateStore(directories.state_path),
        clock=clock,
        **kwargs,
    )


def build_runtime(database_path: Path) -> DatabaseRuntime:
    return DatabaseRuntime(Database(DatabaseConfig(path=database_path)))


def build_factory(
    config_service: ConfigService,
    runtime: DatabaseRuntime | None = None,
    **kwargs: object,
) -> BackupWorkspaceFactory:
    return BackupWorkspaceFactory(
        config_service,
        runtime or DatabaseRuntime(),
        **kwargs,
    )


def insert_probe(database_path: Path, value: str, *, table: str = "probe") -> None:
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            f'CREATE TABLE IF NOT EXISTS {table} (value TEXT NOT NULL)'
        )
        connection.execute(f"INSERT INTO {table} (value) VALUES (?)", (value,))
        connection.commit()
    finally:
        connection.close()


def probe_values(database_path: Path, *, table: str = "probe") -> list[str]:
    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute(f"SELECT value FROM {table} ORDER BY rowid").fetchall()
        return [str(row[0]) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        connection.close()


def write_state(
    directories: BackupDirectories,
    *,
    last_success_utc: datetime | None = None,
    last_success_file: str | None = None,
    last_success_type: str | None = None,
    consecutive_failures: int = 0,
) -> None:
    from app.infrastructure.backup.state import BackupState

    BackupStateStore(directories.state_path).write(
        BackupState(
            last_success_utc=last_success_utc,
            last_success_file=last_success_file,
            last_success_type=last_success_type,
            consecutive_failures=consecutive_failures,
        )
    )


def fixed_clock(moment: datetime):
    """Return a deterministic UTC clock callable."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    def clock() -> datetime:
        return moment

    return clock


def managed_names(root: Path) -> list[str]:
    directories = build_directories(root)
    names: list[str] = []
    for directory in directories.managed:
        if directory.is_dir():
            names.extend(sorted(entry.name for entry in directory.iterdir()))
    return names


def metadata_files(root: Path) -> list[Path]:
    directories = build_directories(root)
    files: list[Path] = []
    for directory in directories.managed:
        if directory.is_dir():
            files.extend(sorted(directory.glob(f"*{constants.BACKUP_METADATA_SUFFIX}")))
    return files


__all__ = [
    "build_backup_service",
    "build_directories",
    "build_factory",
    "build_runtime",
    "create_data_root",
    "create_database_at",
    "fixed_clock",
    "insert_probe",
    "managed_names",
    "metadata_files",
    "probe_values",
    "save_location",
    "write_state",
]
