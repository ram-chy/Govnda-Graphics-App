"""Phase 4 backup service tests: publishing, verification, and failure safety."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.exceptions import BackupError, OperationLockedError
from app.domain.backup import BackupType
from app.infrastructure.backup.hashing import sha256_file
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.metadata import read_metadata
from app.infrastructure.backup.naming import metadata_path_for
from app.infrastructure.backup.snapshot import DatabaseVerification
from app.infrastructure.database.migrations import application_head_revision
from tests.backup_helpers import (
    build_backup_service,
    build_directories,
    build_runtime,
    create_data_root,
    fixed_clock,
    insert_probe,
    probe_values,
)

MOMENT = datetime(2026, 4, 5, 6, 7, 8, tzinfo=UTC)
HEAD_REVISION = application_head_revision()


def _verification(path: Path, *, ok: bool = True) -> DatabaseVerification:
    message = ("ok",) if ok else ("database disk image is malformed",)
    return DatabaseVerification(
        path=path,
        size_bytes=path.stat().st_size if path.exists() else 0,
        application_id=0x47424753,
        user_version=1,
        schema_revision="0001_baseline",
        page_count=1,
        quick_check=message,
        integrity_check=message,
        foreign_key_check=(),
        checks={"test": "yes"},
    )


def test_manual_backup_publishes_verified_file_and_metadata(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    insert_probe(database_path, "first-row")
    service = build_backup_service(root, database_path, clock=fixed_clock(MOMENT))

    result = service.create_backup(BackupType.MANUAL, trigger="manual")

    assert result.path.parent == build_directories(root).manual
    expected_name = f"BusinessManagement_{MOMENT.astimezone():%Y-%m-%d_%H-%M-%S}_MANUAL.db"
    assert result.path.name == expected_name
    assert result.path.is_file()
    assert probe_values(result.path) == ["first-row"]
    assert result.metadata.sha256 == sha256_file(result.path)
    assert result.metadata.backup_bytes == result.path.stat().st_size
    assert result.metadata.schema_revision == HEAD_REVISION
    assert result.metadata.trigger == "manual"
    assert result.verification.ok is True

    loaded = read_metadata(metadata_path_for(result.path))
    assert loaded == result.metadata
    assert loaded.verified is True

    state = service.state_store.read()
    assert state.last_success_file == result.path.name
    assert state.last_success_type == "manual"
    assert state.consecutive_failures == 0
    assert not list(result.path.parent.glob("*.tmp"))


def test_same_second_backups_receive_unique_names(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    service = build_backup_service(root, database_path, clock=fixed_clock(MOMENT))

    first = service.create_backup(BackupType.MANUAL, trigger="manual")
    second = service.create_backup(BackupType.MANUAL, trigger="manual")

    assert first.path != second.path
    assert first.path.name.endswith("_MANUAL.db")
    assert second.path.name.endswith("_MANUAL_2.db")
    assert first.path.is_file() and second.path.is_file()
    assert first.metadata.sha256 == second.metadata.sha256


def test_backup_rejects_a_missing_or_empty_source(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    missing = root / "Database" / "BusinessManagement.db"
    service = build_backup_service(root, missing)

    with pytest.raises(BackupError) as missing_error:
        service.create_backup(BackupType.MANUAL, trigger="manual")
    assert "is missing" in str(missing_error.value)

    missing.parent.mkdir(parents=True)
    missing.write_bytes(b"")
    with pytest.raises(BackupError) as empty_error:
        service.create_backup(BackupType.MANUAL, trigger="manual")
    assert "empty" in str(empty_error.value)

    assert not any(build_directories(root).manual.glob("*.db"))


def test_backup_refuses_insufficient_free_space(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    service = build_backup_service(
        root,
        database_path,
        free_space_provider=lambda _path: 1,
    )

    with pytest.raises(BackupError) as error:
        service.create_backup(BackupType.MANUAL, trigger="manual")

    assert "not enough free space" in error.value.user_message.lower()
    assert not any(build_directories(root).manual.glob("*.db"))


def test_backup_verification_failure_publishes_nothing(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    service = build_backup_service(
        root,
        database_path,
        verifier=lambda path: _verification(path, ok=False),
    )

    with pytest.raises(BackupError):
        service.create_backup(BackupType.MANUAL, trigger="manual")

    directories = build_directories(root)
    assert not any(directories.manual.glob("*.db"))
    assert not any(directories.manual.glob("*.meta.json"))
    assert service.state_store.read().consecutive_failures == 1


def test_backup_rejects_an_unexpected_schema_revision(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    service = build_backup_service(root, database_path)

    with pytest.raises(BackupError) as error:
        service.create_backup(
            BackupType.MANUAL,
            trigger="manual",
            expected_schema_revision="9999_other",
        )

    assert "different schema revision" in error.value.user_message
    assert not any(build_directories(root).manual.glob("*.db"))


def test_lock_contention_prevents_a_second_backup(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    directories = build_directories(root)
    directories.ensure()
    service = build_backup_service(root, database_path)
    holder = OperationLock(directories.lock_path, operation="restore")
    holder.acquire()
    try:
        with pytest.raises(OperationLockedError):
            service.create_backup(BackupType.MANUAL, trigger="manual")
    finally:
        holder.release()

    assert not any(directories.manual.glob("*.db"))


def test_interrupted_snapshot_leaves_no_published_file(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)

    def fail_snapshot(*_args, **_kwargs):
        raise BackupError(
            "simulated interrupted snapshot",
            user_message="simulated interrupted snapshot",
        )

    service = build_backup_service(root, database_path, snapshotter=fail_snapshot)

    with pytest.raises(BackupError):
        service.create_backup(BackupType.MANUAL, trigger="manual")

    directories = build_directories(root)
    assert not any(directories.manual.glob("*.db"))
    assert not any(directories.manual.glob("*.meta.json"))
    state = service.state_store.read()
    assert state.consecutive_failures == 1
    assert "simulated interrupted snapshot" in (state.last_failure_message or "")
    assert directories.last_error_path.is_file()


def test_stale_temporary_files_are_removed_before_a_backup(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    directories = build_directories(root)
    directories.ensure()
    stale = directories.manual / ".BusinessManagement_old.db.tmp"
    stale.write_bytes(b"abandoned")
    os.utime(stale, (1_000, 1_000))

    service = build_backup_service(root, database_path, clock=fixed_clock(MOMENT))
    service.create_backup(BackupType.MANUAL, trigger="manual")

    assert not stale.exists()
    assert any(directories.manual.glob("*.db"))


def test_safety_backup_accepts_an_already_held_lock(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    directories = build_directories(root)
    directories.ensure()
    service = build_backup_service(root, database_path, clock=fixed_clock(MOMENT))

    holder = OperationLock(directories.lock_path, operation="restore")
    holder.acquire()
    try:
        result = service.create_backup(
            BackupType.SAFETY,
            trigger="restore",
            assume_locked=True,
        )
    finally:
        holder.release()

    assert result.path.parent == directories.safety
    assert result.path.is_file()


def test_backup_state_remains_readable_after_a_failure(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    service = build_backup_service(root, database_path)
    service.create_backup(BackupType.MANUAL, trigger="manual")

    missing_root = tmp_path / "Other"
    broken = build_backup_service(missing_root, missing_root / "Database" / "Missing.db")
    with pytest.raises(BackupError):
        broken.create_backup(BackupType.MANUAL, trigger="manual")

    state = service.state_store.read()
    assert state.last_success_file is not None
    assert state.last_attempt_result == "success"


def test_backup_service_exposes_its_runtime_paths(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    runtime = build_runtime(database_path)
    try:
        service = build_backup_service(root, database_path)
        assert service.database_path == database_path
        assert service.directories.root == root / "Backups"
        assert runtime.path == database_path
    finally:
        runtime.close()
