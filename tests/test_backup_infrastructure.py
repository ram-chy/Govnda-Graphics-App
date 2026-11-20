"""Phase 4 infrastructure tests: naming, metadata, history, locks, retention, snapshots."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core import constants
from app.core.exceptions import BackupError, OperationLockedError
from app.domain.backup import BackupRecord, BackupStatus, BackupType
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.hashing import sha256_file
from app.infrastructure.backup.history import BackupHistory
from app.infrastructure.backup.lock import LockOwner, OperationLock
from app.infrastructure.backup.metadata import (
    BackupMetadata,
    MetadataError,
    read_metadata,
    write_metadata_atomic,
)
from app.infrastructure.backup.naming import (
    backup_file_name,
    backup_stem,
    is_managed_backup_name,
    metadata_path_for,
    temp_path_for,
)
from app.infrastructure.backup.retention import RetentionExecutor
from app.infrastructure.backup.snapshot import (
    clean_stale_temporary_files,
    create_snapshot,
    read_database_revision,
    verify_database_file,
    verify_writable,
)
from app.infrastructure.database.migrations import application_head_revision
from app.infrastructure.filesystem.layout import DataRootLayout
from tests.backup_helpers import create_database_at, insert_probe, probe_values

HEAD_REVISION = application_head_revision()

CREATED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def _metadata(
    file_name: str,
    *,
    backup_type: BackupType = BackupType.MANUAL,
    backup_bytes: int = 10,
    sha256: str | None = None,
    **overrides: object,
) -> BackupMetadata:
    values: dict[str, object] = {
        "file_name": file_name,
        "backup_type": backup_type,
        "created_at_utc": CREATED,
        "app_version": "0.4.0",
        "application_id": 0x47424753,
        "schema_revision": "0001_baseline",
        "source_database_path": "C:/data/Database/BusinessManagement.db",
        "source_database_bytes": 100,
        "backup_bytes": backup_bytes,
        "sha256": sha256 or "a" * 64,
        "verification_result": "verified",
        "integrity_check": "ok",
        "foreign_key_check": "ok",
        "operation_result": "success",
        "duration_ms": 5,
        "trigger": "manual",
    }
    values.update(overrides)
    return BackupMetadata(**values)  # type: ignore[arg-type]


def _directories(root: Path) -> BackupDirectories:
    directories = BackupDirectories.from_layout(DataRootLayout(root))
    directories.ensure()
    return directories


def _write_backup(
    directory: Path,
    name: str,
    *,
    metadata: BackupMetadata | None = None,
    data: bytes = b"backup-content",
) -> Path:
    path = directory / name
    path.write_bytes(data)
    if metadata is not None:
        write_metadata_atomic(metadata_path_for(path), metadata)
    return path


# -- naming -----------------------------------------------------------------


def test_backup_names_are_sortable_unique_and_type_specific() -> None:
    automatic = backup_file_name(BackupType.AUTOMATIC, CREATED)
    manual = backup_file_name(BackupType.MANUAL, CREATED)

    assert automatic == "BusinessManagement_2026-01-02_03-04-05_AUTOMATIC.db"
    assert manual.endswith("_MANUAL.db")
    assert is_managed_backup_name(automatic)
    assert is_managed_backup_name("BusinessManagement_2026-01-02_03-04-05_MANUAL_2.db")
    assert not is_managed_backup_name("BusinessManagement_notes.db")
    assert not is_managed_backup_name("Foreign.db")
    assert backup_stem(BackupType.SAFETY, CREATED).endswith("_SAFETY")


def test_backup_name_collision_adds_a_suffix_case_insensitively() -> None:
    first = backup_file_name(BackupType.MANUAL, CREATED)
    second = backup_file_name(BackupType.MANUAL, CREATED, existing_names=[first.upper()])

    assert second == "BusinessManagement_2026-01-02_03-04-05_MANUAL_2.db"


def test_metadata_and_temporary_paths_are_distinct() -> None:
    target = Path("Backups") / "BusinessManagement_2026-01-02_03-04-05_MANUAL.db"

    assert metadata_path_for(target).name == f"{target.name}{constants.BACKUP_METADATA_SUFFIX}"
    first = temp_path_for(target)
    second = temp_path_for(target)
    assert first != second
    assert first.name.startswith(".")
    assert first.name.endswith(constants.BACKUP_TEMP_SUFFIX)


# -- metadata ---------------------------------------------------------------


def test_metadata_round_trips_through_an_atomic_sidecar(tmp_path: Path) -> None:
    path = tmp_path / "backup.db.meta.json"
    metadata = _metadata("backup.db")

    write_metadata_atomic(path, metadata)
    loaded = read_metadata(path)

    assert loaded == metadata
    assert loaded.verified is True
    assert loaded.to_dict()["created_at_utc"].endswith("Z")


@pytest.mark.parametrize(
    "overrides",
    [
        {"meta_version": 99},
        {"file_name": ""},
        {"sha256": "not-a-digest"},
        {"backup_bytes": 0},
        {"backup_type": "unknown"},
    ],
)
def test_invalid_metadata_is_rejected(overrides: dict[str, object]) -> None:
    data = _metadata("backup.db").to_dict()
    data.update(overrides)

    with pytest.raises(MetadataError):
        BackupMetadata.from_dict(data)


def test_metadata_reader_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.meta.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(MetadataError):
        read_metadata(path)


# -- history ----------------------------------------------------------------


def test_history_classifies_every_backup_file(tmp_path: Path) -> None:
    directories = _directories(tmp_path / "Business")
    verified_name = "BusinessManagement_2026-01-02_03-04-05_AUTOMATIC.db"
    verified = _write_backup(
        directories.automatic,
        verified_name,
        metadata=_metadata(
            verified_name,
            backup_type=BackupType.AUTOMATIC,
            backup_bytes=len(b"backup-content"),
        ),
    )
    assert verified.is_file()

    _write_backup(directories.automatic, "BusinessManagement_2026-01-01_03-04-05_AUTOMATIC.db")
    _write_backup(
        directories.automatic,
        "BusinessManagement_2026-01-03_03-04-05_AUTOMATIC.db",
        metadata=_metadata(
            "BusinessManagement_2026-01-03_03-04-05_AUTOMATIC.db",
            backup_type=BackupType.AUTOMATIC,
            backup_bytes=999,
        ),
    )
    _write_backup(
        directories.manual,
        "BusinessManagement_2026-01-04_03-04-05_MANUAL.db",
        metadata=_metadata(
            "BusinessManagement_2026-01-04_03-04-05_MANUAL.db",
            backup_type=BackupType.AUTOMATIC,
        ),
    )
    bad = directories.manual / "BusinessManagement_2026-01-05_03-04-05_MANUAL.db"
    bad.write_bytes(b"x")
    metadata_path_for(bad).write_text("{bad", encoding="utf-8")

    orphan_name = "BusinessManagement_2026-01-06_03-04-05_SAFETY.db"
    write_metadata_atomic(
        directories.safety / f"{orphan_name}{constants.BACKUP_METADATA_SUFFIX}",
        _metadata(orphan_name, backup_type=BackupType.SAFETY),
    )

    scan = BackupHistory(directories).scan()
    statuses = {record.file_name: record.status for record in scan.records}

    assert statuses[verified_name] is BackupStatus.VERIFIED
    assert statuses["BusinessManagement_2026-01-01_03-04-05_AUTOMATIC.db"] is (
        BackupStatus.UNVERIFIED
    )
    assert statuses["BusinessManagement_2026-01-03_03-04-05_AUTOMATIC.db"] is (
        BackupStatus.UNVERIFIED
    )
    assert statuses["BusinessManagement_2026-01-04_03-04-05_MANUAL.db"] is (
        BackupStatus.MALFORMED
    )
    assert statuses[bad.name] is BackupStatus.MALFORMED
    assert statuses[orphan_name] is BackupStatus.MISSING
    assert scan.latest(verified_only=True).file_name == verified_name


def test_history_ignores_hidden_files_and_unmanaged_names(tmp_path: Path) -> None:
    directories = _directories(tmp_path / "Business")
    (directories.manual / ".temporary.tmp").write_bytes(b"x")
    (directories.manual / "notes.txt").write_text("x", encoding="utf-8")
    (directories.manual / "Foreign.db").write_bytes(b"x")

    records = BackupHistory(directories).scan().records

    # A foreign .db file is listed honestly as unverified, but hidden temporary
    # files and non-database files are never part of history.
    assert [record.file_name for record in records] == ["Foreign.db"]
    assert records[0].status is BackupStatus.UNVERIFIED


# -- operation lock ---------------------------------------------------------


def _owner(pid: int, token: str = "owner") -> LockOwner:
    return LockOwner(
        token=token,
        pid=pid,
        process_name="python.exe",
        operation="backup",
        created_at_utc=datetime.now(UTC),
    )


def test_lock_is_exclusive_and_released_by_its_owner(tmp_path: Path) -> None:
    path = tmp_path / "Backups" / ".backup.lock"
    first = OperationLock(path, operation="backup")
    second = OperationLock(path, operation="restore")

    first.acquire()
    try:
        assert path.is_file()
        with pytest.raises(OperationLockedError):
            second.acquire()
    finally:
        first.release()

    assert not path.exists()
    assert first.acquired is False


def test_stale_lock_is_reclaimed_only_for_a_dead_owner(tmp_path: Path) -> None:
    path = tmp_path / "Backups" / ".backup.lock"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_owner(999_999).to_dict()), encoding="utf-8")

    lock = OperationLock(path, operation="restore", process_alive=lambda _pid: False)
    lock.acquire()
    try:
        assert lock.acquired is True
        assert json.loads(path.read_text(encoding="utf-8"))["token"] == lock.owner.token
    finally:
        lock.release()


def test_unreadable_lock_is_treated_as_held(tmp_path: Path) -> None:
    path = tmp_path / "Backups" / ".backup.lock"
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(OperationLockedError):
        OperationLock(path, operation="backup").acquire()

    assert path.exists()


def test_release_never_deletes_a_lock_with_another_token(tmp_path: Path) -> None:
    path = tmp_path / "Backups" / ".backup.lock"
    lock = OperationLock(path, operation="backup")
    lock.acquire()
    replacement = _owner(os.getpid(), token="another-owner")
    path.write_text(json.dumps(replacement.to_dict()), encoding="utf-8")

    lock.release()

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == "another-owner"


def test_a_live_reclaim_guard_blocks_stale_lock_recovery(tmp_path: Path) -> None:
    path = tmp_path / "Backups" / ".backup.lock"
    guard = path.with_name(f"{path.name}{constants.LOCK_RECLAIM_SUFFIX}")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_owner(999_999).to_dict()), encoding="utf-8")
    guard.write_text(json.dumps(_owner(os.getpid(), token="guard").to_dict()), encoding="utf-8")

    lock = OperationLock(
        path,
        operation="backup",
        process_alive=lambda pid: pid == os.getpid(),
    )
    with pytest.raises(OperationLockedError):
        lock.acquire()

    assert path.exists()
    assert guard.exists()


# -- retention --------------------------------------------------------------


def test_retention_executor_deletes_only_selected_managed_files(tmp_path: Path) -> None:
    directories = _directories(tmp_path / "Business")
    old_name = "BusinessManagement_2025-01-01_10-00-00_AUTOMATIC.db"
    old = _write_backup(directories.automatic, old_name)
    write_metadata_atomic(
        metadata_path_for(old),
        _metadata(old_name, backup_type=BackupType.AUTOMATIC),
    )
    newer_name = "BusinessManagement_2026-05-01_10-00-00_AUTOMATIC.db"
    newer = _write_backup(directories.automatic, newer_name)
    write_metadata_atomic(
        metadata_path_for(newer),
        _metadata(newer_name, backup_type=BackupType.AUTOMATIC),
    )
    manual = _write_backup(
        directories.manual,
        "BusinessManagement_2025-01-01_10-00-00_MANUAL.db",
    )
    unrelated = directories.automatic / "UserCopy.db"
    unrelated.write_bytes(b"keep")
    outside = tmp_path / "outside.db"
    outside.write_bytes(b"keep")

    now = datetime(2026, 6, 1, tzinfo=UTC)
    old_record = BackupRecord(
        path=old,
        backup_type=BackupType.AUTOMATIC,
        status=BackupStatus.VERIFIED,
        file_name=old.name,
        created_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        size_bytes=10,
    )
    newer_record = BackupRecord(
        path=newer,
        backup_type=BackupType.AUTOMATIC,
        status=BackupStatus.VERIFIED,
        file_name=newer.name,
        created_at_utc=datetime(2026, 5, 1, tzinfo=UTC),
        size_bytes=10,
    )
    manual_record = BackupRecord(
        path=manual,
        backup_type=BackupType.MANUAL,
        status=BackupStatus.VERIFIED,
        file_name=manual.name,
        created_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        size_bytes=10,
    )
    outside_record = BackupRecord(
        path=outside,
        backup_type=BackupType.AUTOMATIC,
        status=BackupStatus.VERIFIED,
        file_name="BusinessManagement_2020-01-01_10-00-00_AUTOMATIC.db",
        created_at_utc=datetime(2020, 1, 1, tzinfo=UTC),
        size_bytes=10,
    )

    result = RetentionExecutor(directories).apply(
        [newer_record, old_record, manual_record, outside_record],
        now_utc=now,
        retention_days=30,
        keep_minimum=1,
    )

    assert result.deleted == (old,)
    assert not old.exists()
    assert not metadata_path_for(old).exists()
    assert newer.exists()
    assert manual.exists()
    assert unrelated.exists()
    assert outside.exists()
    assert any("unmanaged path" in error for error in result.errors)


def test_retention_executor_removes_only_stale_application_tempfiles(tmp_path: Path) -> None:
    directories = _directories(tmp_path / "Business")
    stale = directories.automatic / ".backup.db.old.tmp"
    fresh = directories.automatic / ".backup.db.fresh.tmp"
    plain = directories.automatic / "notes.tmp"
    for path in (stale, fresh, plain):
        path.write_bytes(b"x")
    old_time = 1_000_000.0
    os.utime(stale, (old_time, old_time))

    result = RetentionExecutor(directories).apply(
        [],
        now_utc=datetime.now(UTC),
        retention_days=30,
        keep_minimum=1,
    )

    assert stale not in result.deleted
    assert not stale.exists()
    assert fresh.exists()
    assert plain.exists()
    assert stale in result.stale_temporary_files


# -- snapshot and verification ---------------------------------------------


def test_snapshot_includes_wal_content_from_an_active_connection(tmp_path: Path) -> None:
    database_path = create_database_at(tmp_path / "live.db")
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        insert_probe(database_path, "committed-to-wal")
        assert (database_path.parent / f"{database_path.name}-wal").exists()

        snapshot = tmp_path / "snapshot.db"
        result = create_snapshot(database_path, snapshot)

        assert result.pages_copied > 0
        assert result.backup_bytes == snapshot.stat().st_size
        assert probe_values(snapshot) == ["committed-to-wal"]
        verification = verify_database_file(snapshot)
        assert verification.ok is True
        assert verification.schema_revision == HEAD_REVISION
        assert read_database_revision(snapshot) == HEAD_REVISION
        assert verify_writable(snapshot) == (True, "ok")
    finally:
        connection.close()


def test_snapshot_refuses_to_overwrite_an_existing_destination(tmp_path: Path) -> None:
    database_path = create_database_at(tmp_path / "live.db")
    destination = tmp_path / "exists.db"
    destination.write_bytes(b"old")

    with pytest.raises(BackupError):
        create_snapshot(database_path, destination)

    assert destination.read_bytes() == b"old"


def test_snapshot_reports_missing_and_empty_sources(tmp_path: Path) -> None:
    with pytest.raises(BackupError):
        create_snapshot(tmp_path / "missing.db", tmp_path / "snapshot.db")

    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    with pytest.raises(BackupError):
        create_snapshot(empty, tmp_path / "snapshot.db")


def test_verification_reports_a_corrupt_database_without_raising(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not sqlite" * 20)

    result = verify_database_file(corrupt)
    assert result.ok is False
    assert result.application_id is None
    assert "failed" in result.failure_summary.lower() or "quick_check" in result.failure_summary
    assert read_database_revision(corrupt) is None

    missing = verify_database_file(tmp_path / "missing.db")
    assert missing.ok is False
    assert missing.size_bytes == 0


def test_verification_does_not_accept_a_foreign_application_id(tmp_path: Path) -> None:
    database_path = create_database_at(tmp_path / "live.db")
    path = tmp_path / "snapshot.db"
    create_snapshot(database_path, path)
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("PRAGMA application_id = 12345")
        connection.commit()
    finally:
        connection.close()

    result = verify_database_file(path)
    assert result.identity_ok is False
    assert result.ok is False


def test_stale_temporary_cleanup_uses_age_and_the_application_prefix(tmp_path: Path) -> None:
    stale = tmp_path / ".BusinessManagement_old.db.tmp"
    fresh = tmp_path / ".BusinessManagement_fresh.db.tmp"
    unrelated = tmp_path / "other.tmp"
    for path in (stale, fresh, unrelated):
        path.write_bytes(b"x")
    os.utime(stale, (1_000_000, 1_000_000))

    removed = clean_stale_temporary_files(
        tmp_path,
        older_than_seconds=60,
        now_timestamp=2_000_000,
    )

    assert removed == (stale,)
    assert not stale.exists()
    assert fresh.exists()
    assert unrelated.exists()


def test_sha256_of_a_snapshot_matches_the_published_bytes(tmp_path: Path) -> None:
    database_path = create_database_at(tmp_path / "live.db")
    snapshot = tmp_path / "snapshot.db"
    result = create_snapshot(database_path, snapshot)

    assert result.sha256 == sha256_file(snapshot)
    assert len(result.sha256) == 64
