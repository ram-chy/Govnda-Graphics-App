"""Pure Phase 4 backup policy tests (no filesystem, SQLite, or Qt)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.domain.backup import (
    BackupRecord,
    BackupStatus,
    BackupType,
    catch_up_decision,
    parse_due_time,
    select_retention_candidates,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _record(
    name: str,
    created: datetime,
    *,
    backup_type: BackupType = BackupType.AUTOMATIC,
    status: BackupStatus = BackupStatus.VERIFIED,
) -> BackupRecord:
    return BackupRecord(
        path=Path("Backups") / name,
        backup_type=backup_type,
        status=status,
        file_name=name,
        created_at_utc=created,
        size_bytes=1024,
    )


def test_parse_due_time_requires_two_digit_clock_values() -> None:
    assert parse_due_time("22:05") == (22, 5)
    assert parse_due_time("00:00") == (0, 0)

    for value in ("22", "2:05", "24:00", "22:60", "aa:bb", ""):
        with pytest.raises(ValueError):
            parse_due_time(value)


def test_catch_up_is_not_due_when_disabled() -> None:
    decision = catch_up_decision(
        enabled=False,
        now_local=datetime(2026, 6, 1, 23, 0),
        due_time="22:00",
        last_success_local=None,
    )

    assert decision.due is False
    assert "disabled" in decision.reason


def test_catch_up_runs_once_when_no_success_is_recorded() -> None:
    decision = catch_up_decision(
        enabled=True,
        now_local=datetime(2026, 6, 1, 8, 0),
        due_time="22:00",
        last_success_local=None,
    )

    assert decision.due is True
    assert "no successful" in decision.reason


def test_catch_up_after_todays_due_time_when_last_success_is_older() -> None:
    decision = catch_up_decision(
        enabled=True,
        now_local=datetime(2026, 6, 1, 23, 0),
        due_time="22:00",
        last_success_local=datetime(2026, 6, 1, 21, 0),
    )

    assert decision.due is True
    assert "passed" in decision.reason


def test_catch_up_never_duplicates_todays_success() -> None:
    decision = catch_up_decision(
        enabled=True,
        now_local=datetime(2026, 6, 1, 23, 30),
        due_time="22:00",
        last_success_local=datetime(2026, 6, 1, 22, 5),
    )

    assert decision.due is False
    assert "already completed" in decision.reason


def test_elapsed_guard_catches_up_a_missed_previous_day() -> None:
    decision = catch_up_decision(
        enabled=True,
        now_local=datetime(2026, 6, 1, 8, 0),
        due_time="22:00",
        last_success_local=datetime(2026, 5, 30, 8, 0),
        elapsed_guard_hours=36,
    )

    assert decision.due is True
    assert "older than 36 hours" in decision.reason


def test_not_due_before_todays_time_within_elapsed_guard() -> None:
    decision = catch_up_decision(
        enabled=True,
        now_local=datetime(2026, 6, 1, 8, 0),
        due_time="22:00",
        last_success_local=datetime(2026, 5, 31, 22, 0),
    )

    assert decision.due is False
    assert "not due yet" in decision.reason


def test_retention_only_targets_old_verified_automatic_backups() -> None:
    records = (
        _record("auto-old.db", NOW - timedelta(days=120)),
        _record("auto-middle.db", NOW - timedelta(days=45)),
        _record("auto-current.db", NOW - timedelta(days=3)),
        _record(
            "manual-old.db",
            NOW - timedelta(days=400),
            backup_type=BackupType.MANUAL,
        ),
        _record(
            "safety-old.db",
            NOW - timedelta(days=400),
            backup_type=BackupType.SAFETY,
        ),
        _record(
            "auto-unverified.db",
            NOW - timedelta(days=400),
            status=BackupStatus.UNVERIFIED,
        ),
    )

    candidates = select_retention_candidates(
        records,
        now_utc=NOW,
        retention_days=30,
        keep_minimum=1,
    )

    assert {record.file_name for record in candidates} == {
        "auto-old.db",
        "auto-middle.db",
    }


def test_retention_protects_the_newest_backup_of_any_type() -> None:
    records = (
        _record(
            "manual-newest.db",
            NOW - timedelta(days=200),
            backup_type=BackupType.MANUAL,
        ),
        _record("auto-old.db", NOW - timedelta(days=180)),
        _record("auto-newer.db", NOW - timedelta(days=90)),
    )

    candidates = select_retention_candidates(
        records,
        now_utc=NOW,
        retention_days=30,
        keep_minimum=1,
    )

    # ``manual-newest`` is the newest verified backup, so it is retained even
    # though it is outside the retention window. The newest automatic backup is
    # also protected by ``keep_minimum``.
    assert [record.file_name for record in candidates] == ["auto-old.db"]


def test_retention_always_keeps_at_least_one_verified_backup() -> None:
    only = _record("only.db", NOW - timedelta(days=400))

    assert (
        select_retention_candidates(
            (only,), now_utc=NOW, retention_days=1, keep_minimum=1
        )
        == ()
    )


def test_retention_keeps_recent_backups_and_rejects_invalid_settings() -> None:
    recent = _record("recent.db", NOW - timedelta(days=1))

    assert (
        select_retention_candidates(
            (recent,), now_utc=NOW, retention_days=30, keep_minimum=5
        )
        == ()
    )
    with pytest.raises(ValueError):
        select_retention_candidates((recent,), now_utc=NOW, retention_days=0, keep_minimum=1)
    with pytest.raises(ValueError):
        select_retention_candidates((recent,), now_utc=NOW, retention_days=1, keep_minimum=0)


def test_retention_never_qualifies_records_without_a_trusted_timestamp() -> None:
    record = BackupRecord(
        path=Path("Backups") / "unknown.db",
        backup_type=BackupType.AUTOMATIC,
        status=BackupStatus.VERIFIED,
        file_name="unknown.db",
        created_at_utc=None,
    )

    assert (
        select_retention_candidates(
            (record,), now_utc=NOW, retention_days=30, keep_minimum=1
        )
        == ()
    )
