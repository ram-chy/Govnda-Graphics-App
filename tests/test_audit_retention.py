"""Audit retention, append-only enforcement, and backup/restore preservation."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DomainRuleError, MigrationError, RestoreError
from app.domain.backup import BackupType
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.database.audit_history import read_audit_rows, verify_audit_structure
from app.infrastructure.database.business_profile_repository import AuditEventRepository
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import MigrationManager, application_head_revision
from app.infrastructure.database.models.business_profile import AuditEventRecord
from app.infrastructure.database.repository import Repository
from app.services.backup_service import BackupService
from app.services.restore_service import RestoreService
from tests.backup_helpers import (
    build_directories,
    build_runtime,
    create_data_root,
    fixed_clock,
    save_location,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HEAD_REVISION = application_head_revision()
MOMENT = datetime(2026, 11, 21, 10, 30, tzinfo=UTC)


def _insert_audit(
    path: Path,
    event_id: int,
    event_type: str = "business_profile.updated",
    created_at: str = "2026-11-21T10:00:00Z",
) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.execute(
            "INSERT INTO audit_events "
            "(id, event_type, entity_type, entity_id, actor, created_at, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                event_type,
                "business_profile",
                "1",
                "system/unauthenticated",
                created_at,
                f'{{"id":{event_id}}}',
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _backup_service(
    root: Path, database_path: Path, *, managed_asset_dirs: tuple[Path, ...] = ()
) -> BackupService:
    directories = build_directories(root)
    return BackupService(
        directories=directories,
        database_path=database_path,
        lock=OperationLock(directories.lock_path, operation="backup"),
        state_store=BackupStateStore(directories.state_path),
        clock=fixed_clock(MOMENT),
        managed_asset_dirs=managed_asset_dirs,
    )


def _restore_service(
    config_service, runtime, root: Path, backup_service: BackupService
) -> RestoreService:
    directories = build_directories(root)
    return RestoreService(
        config_service=config_service,
        runtime=runtime,
        directories=directories,
        lock=OperationLock(directories.lock_path, operation="restore"),
        backup_service=backup_service,
        expected_schema_revision=HEAD_REVISION,
        state_store=BackupStateStore(directories.state_path),
        clock=fixed_clock(MOMENT),
    )


def test_audit_event_insertion_and_database_immutability(
    initialized_database: Database,
) -> None:
    path = initialized_database.config.path
    _insert_audit(path, 1, "business_profile.created")

    rows = read_audit_rows(path)
    assert len(rows) == 1
    assert rows[0].event_type == "business_profile.created"

    with pytest.raises(IntegrityError), initialized_database.engine.begin() as connection:
        connection.execute(text("UPDATE audit_events SET actor = 'changed'"))
    with pytest.raises(IntegrityError), initialized_database.engine.begin() as connection:
        connection.execute(text("DELETE FROM audit_events"))

    assert read_audit_rows(path)[0].actor == "system/unauthenticated"
    assert not hasattr(AuditEventRepository, "delete")
    assert not hasattr(AuditEventRepository, "update")


def test_orm_and_generic_repository_refuse_immutable_changes(
    initialized_database: Database,
) -> None:
    path = initialized_database.config.path
    _insert_audit(path, 2)

    with pytest.raises(DomainRuleError), initialized_database.unit_of_work() as work:
        record = work.session.get(AuditEventRecord, 2)
        assert record is not None
        record.actor = "changed"
        work.commit()

    with pytest.raises(DomainRuleError), initialized_database.unit_of_work() as work:
        record = work.session.get(AuditEventRecord, 2)
        assert record is not None
        work.session.delete(record)
        work.commit()

    with pytest.raises(DomainRuleError), initialized_database.unit_of_work() as work:
        entity = AuditEventRecord(
            id=99,
            event_type="business_profile.updated",
            entity_type="business_profile",
            entity_id="1",
            actor="system/unauthenticated",
            created_at="2026-11-21T10:00:00Z",
            payload="{}",
        )
        Repository(work.session, AuditEventRecord).delete(entity)

    assert read_audit_rows(path)[0].actor == "system/unauthenticated"


def test_audit_schema_has_no_expiry_column_and_keeps_immutability_triggers(
    initialized_database: Database,
) -> None:
    with initialized_database.engine.connect() as connection:
        columns = [
            str(row[1])
            for row in connection.exec_driver_sql("PRAGMA table_info(audit_events)").fetchall()
        ]
        triggers = {
            str(row[0])
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'trigger' AND tbl_name = 'audit_events'"
            ).fetchall()
        }

    assert columns == [
        "id",
        "event_type",
        "entity_type",
        "entity_id",
        "actor",
        "created_at",
        "payload",
    ]
    assert {"trg_audit_events_no_update", "trg_audit_events_no_delete"} <= triggers


def test_no_automatic_audit_cleanup_or_scheduled_purge() -> None:
    forbidden_sql = re.compile(
        r"(?i)\b(?:delete\s+from|truncate\s+table|update|drop\s+table)\s+audit_events\b"
        r"|\baudit_events\s+set\b"
    )
    sources = [
        *sorted((REPO_ROOT / "app").rglob("*.py")),
        *sorted((REPO_ROOT / "migrations").rglob("*.py")),
    ]
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in sources
        if forbidden_sql.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []

    audit_free_sources = [
        REPO_ROOT / "app/core/constants.py",
        REPO_ROOT / "app/services/schedule_service.py",
        REPO_ROOT / "app/infrastructure/backup/task_scheduler.py",
        REPO_ROOT / "app/services/retention_service.py",
        REPO_ROOT / "app/infrastructure/backup/retention.py",
    ]
    assert all(
        "audit" not in path.read_text(encoding="utf-8").casefold()
        for path in audit_free_sources
    )


def test_downgrade_refuses_to_destroy_audit_history(initialized_database: Database) -> None:
    path = initialized_database.config.path
    _insert_audit(path, 3)
    manager = MigrationManager(initialized_database)

    with pytest.raises(MigrationError, match="audit history"):
        manager.downgrade("0002_business_profile")
    assert manager.current_revision() == HEAD_REVISION
    assert [row.id for row in read_audit_rows(path)] == [3]

    with pytest.raises(MigrationError, match="audit history"):
        manager.downgrade("base")
    assert manager.current_revision() == HEAD_REVISION
    assert [row.id for row in read_audit_rows(path)] == [3]


def test_upgrade_preserves_profile_and_creates_protected_audit_history(
    initialized_database: Database,
) -> None:
    manager = MigrationManager(initialized_database)
    manager.downgrade("0002_business_profile")
    with initialized_database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO business_profile "
                "(id, business_name, created_at, updated_at) "
                "VALUES (1, 'Existing Business', 'past', 'past')"
            )
        )

    manager.upgrade("0003_business_profile_requirements")

    with initialized_database.engine.connect() as connection:
        name = connection.execute(
            text("SELECT business_name FROM business_profile WHERE id = 1")
        ).scalar_one()
    assert name == "Existing Business"
    assert [row.event_type for row in read_audit_rows(initialized_database.config.path)] == [
        "business_profile.created"
    ]
    verify_audit_structure(initialized_database.config.path)


def test_backup_and_restore_preserve_all_audit_events(
    tmp_path: Path, config_service
) -> None:
    root, database_path = create_data_root(tmp_path)
    _insert_audit(database_path, 1, "business_profile.created", "2026-11-21T09:00:00Z")
    _insert_audit(database_path, 2, "business_profile.logo_changed", "2026-11-21T09:01:00Z")
    backup_service = _backup_service(root, database_path)
    backup = backup_service.create_backup(BackupType.MANUAL, trigger="manual")

    assert {row.id for row in read_audit_rows(backup.path)} == {1, 2}

    _insert_audit(database_path, 3, "business_profile.updated", "2026-11-21T09:02:00Z")
    save_location(config_service, root, database_path)
    runtime = build_runtime(database_path)
    try:
        service = _restore_service(config_service, runtime, root, backup_service)
        result = service.restore(service.prepare(backup.record))

        assert result.audit_events_preserved == 1
        rows = read_audit_rows(database_path)
        assert {row.id for row in rows} == {1, 2, 3}
        assert {row.created_at for row in rows} == {
            "2026-11-21T09:00:00Z",
            "2026-11-21T09:01:00Z",
            "2026-11-21T09:02:00Z",
        }
        verify_audit_structure(database_path)
        connection = sqlite3.connect(str(database_path))
        try:
            with pytest.raises(sqlite3.IntegrityError), connection:
                connection.execute("UPDATE audit_events SET actor = 'changed'")
        finally:
            connection.close()
    finally:
        runtime.close()


def test_failed_restore_preserves_pre_restore_audit_records(
    tmp_path: Path, config_service, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, database_path = create_data_root(tmp_path)
    logos = root / "Logos"
    logos.mkdir(parents=True, exist_ok=True)
    (logos / "logo.png").write_bytes(b"logo")
    backup_service = _backup_service(root, database_path, managed_asset_dirs=(logos,))
    backup = backup_service.create_backup(BackupType.MANUAL, trigger="manual")
    _insert_audit(database_path, 1, "business_profile.created")
    _insert_audit(database_path, 2, "business_profile.updated")
    save_location(config_service, root, database_path)
    runtime = build_runtime(database_path)
    service = _restore_service(config_service, runtime, root, backup_service)

    def fail_asset_replacement(*_args: object) -> None:
        raise RestoreError("simulated managed asset failure")

    monkeypatch.setattr(service, "_replace_managed_assets", fail_asset_replacement)

    with pytest.raises(RestoreError, match="rolled back"):
        service.restore(service.prepare(backup.record))

    assert {row.id for row in read_audit_rows(database_path)} == {1, 2}
    verify_audit_structure(database_path)
    runtime.close()
