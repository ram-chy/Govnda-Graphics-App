"""Phase 4 startup catch-up tests: policy facts, locking, and failure handling."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import ConfigService
from app.domain.backup import BackupType
from app.infrastructure.backup.lock import OperationLock
from tests.backup_helpers import (
    build_directories,
    build_factory,
    build_runtime,
    create_data_root,
    fixed_clock,
    probe_values,
    save_location,
    write_state,
)

NOW = datetime(2026, 3, 1, 23, 0, tzinfo=UTC)


def _workspace(
    tmp_path: Path,
    *,
    enabled: bool = True,
    moment: datetime = NOW,
    clock=None,
):
    root, database_path = create_data_root(tmp_path)
    config_service = ConfigService(tmp_path / "config" / "config.json")
    save_location(
        config_service,
        root,
        database_path,
        backup_enabled=enabled,
        backup_time="22:00",
    )
    factory = build_factory(
        config_service,
        build_runtime(database_path),
        clock=clock or fixed_clock(moment),
    )
    return factory.build(), root, database_path, config_service


def test_catch_up_runs_when_no_successful_backup_exists(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path)

    result = workspace.catch_up_service.run()

    assert result.attempted is True
    assert result.success is True
    assert result.backup_file is not None
    assert result.backup_file.endswith("_AUTOMATIC.db")
    directories = build_directories(root)
    backup = directories.automatic / str(result.backup_file)
    assert backup.is_file()
    assert probe_values(backup) == []
    assert workspace.state_store.read().last_success_file == result.backup_file


def test_catch_up_is_skipped_when_disabled(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path, enabled=False)

    result = workspace.catch_up_service.run()

    assert result.attempted is False
    assert result.success is False
    assert "disabled" in result.message
    assert not list(build_directories(root).automatic.glob("*.db"))


def test_catch_up_skips_a_success_after_todays_due_time(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path)
    write_state(
        build_directories(root),
        last_success_utc=datetime(2026, 3, 1, 22, 30, tzinfo=UTC),
        last_success_file="already-done.db",
        last_success_type="automatic",
    )

    decision = workspace.catch_up_service.evaluate()
    result = workspace.catch_up_service.run()

    assert decision.due is False
    assert "already completed" in decision.reason
    assert result.attempted is False
    assert not list(build_directories(root).automatic.glob("*.db"))


def test_catch_up_runs_when_todays_due_time_has_passed(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path)
    write_state(
        build_directories(root),
        last_success_utc=datetime(2026, 3, 1, 20, 0, tzinfo=UTC),
        last_success_type="automatic",
    )

    result = workspace.catch_up_service.run()

    assert result.success is True
    assert len(list(build_directories(root).automatic.glob("*.db"))) == 1


def test_catch_up_runs_before_due_time_after_a_long_gap(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(
        tmp_path, moment=datetime(2026, 3, 1, 8, 0, tzinfo=UTC)
    )
    write_state(
        build_directories(root),
        last_success_utc=datetime(2026, 2, 27, 8, 0, tzinfo=UTC),
        last_success_type="automatic",
    )

    decision = workspace.catch_up_service.evaluate()
    result = workspace.catch_up_service.run()

    assert decision.due is True
    assert "older than 36 hours" in decision.reason
    assert result.success is True


def test_catch_up_uses_verified_history_when_state_is_missing(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path)
    workspace.backup_service.create_backup(BackupType.AUTOMATIC, trigger="scheduled")
    # Simulate a lost state file while a verified backup remains on disk.
    workspace.state_store.path.unlink(missing_ok=True)

    decision = workspace.catch_up_service.evaluate()

    assert decision.due is False
    assert "already completed" in decision.reason


def test_catch_up_reports_a_held_lock_without_failing(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path)
    directories = build_directories(root)
    directories.ensure()
    holder = OperationLock(directories.lock_path, operation="restore")
    holder.acquire()
    try:
        result = workspace.catch_up_service.run()
    finally:
        holder.release()

    assert result.attempted is False
    assert result.success is False
    assert result.error is not None
    assert "will be retried" in result.message
    assert not list(directories.automatic.glob("*.db"))


def test_catch_up_reports_a_backup_failure(tmp_path: Path) -> None:
    workspace, _root, database_path, _config = _workspace(tmp_path)
    database_path.unlink()

    result = workspace.catch_up_service.run()

    assert result.attempted is True
    assert result.success is False
    assert result.error is not None
    assert "no backup was created" in result.message.lower()


def test_catch_up_evaluate_never_creates_a_backup(tmp_path: Path) -> None:
    workspace, root, _database, _config = _workspace(tmp_path)

    decision = workspace.catch_up_service.evaluate()

    assert decision.due is True
    assert not list(build_directories(root).automatic.glob("*.db"))
