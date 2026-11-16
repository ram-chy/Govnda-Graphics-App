"""Backup domain language and pure safety decisions.

Nothing here touches a filesystem, SQLite, Qt, or an application service. The
functions implement the policy rules that the backup, retention, and startup
catch-up use cases apply, so those rules can be tested without I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path


class BackupType(StrEnum):
    """The three managed backup categories (BACKUP_STRATEGY.md §2)."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SAFETY = "safety"

    @property
    def label(self) -> str:
        return {
            BackupType.AUTOMATIC: "Automatic",
            BackupType.MANUAL: "Manual",
            BackupType.SAFETY: "Safety",
        }[self]


class BackupStatus(StrEnum):
    """How much a history entry can be trusted without a full re-verification."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MALFORMED = "malformed"
    MISSING = "missing"

    @property
    def label(self) -> str:
        return {
            BackupStatus.VERIFIED: "Verified",
            BackupStatus.UNVERIFIED: "Unverified metadata",
            BackupStatus.MALFORMED: "Malformed metadata",
            BackupStatus.MISSING: "File missing",
        }[self]


@dataclass(frozen=True, slots=True)
class BackupRecord:
    """One backup file discovered on disk, with its sidecar metadata if any."""

    path: Path
    backup_type: BackupType
    status: BackupStatus
    file_name: str
    metadata_path: Path | None = None
    created_at_utc: datetime | None = None
    size_bytes: int | None = None
    schema_revision: str | None = None
    verification_result: str | None = None
    detail: str = ""

    @property
    def file_exists(self) -> bool:
        return self.status is not BackupStatus.MISSING

    @property
    def is_restore_eligible_candidate(self) -> bool:
        """History-level check only; restore performs a fresh full verification."""
        return self.file_exists and self.status is BackupStatus.VERIFIED


@dataclass(frozen=True, slots=True)
class CatchUpDecision:
    """Whether an automatic backup should be attempted at application startup."""

    due: bool
    reason: str
    due_time: str
    last_success_utc: datetime | None = None
    elapsed_hours: float | None = None


def utc_sort_key(value: datetime | None) -> datetime:
    """Return a timezone-aware UTC value that is always safe to compare.

    History records may legitimately carry a naive timestamp (for example from
    hand-written test metadata). Treat naive values as UTC so sorting never
    raises ``TypeError`` for mixing aware and naive datetimes.
    """
    if value is None:
        return datetime.min.replace(tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_due_time(value: str) -> tuple[int, int]:
    """Parse an ``HH:MM`` local time, raising ``ValueError`` when invalid."""
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("time must be HH:MM")
    hour_text, minute_text = parts
    if len(hour_text) != 2 or len(minute_text) != 2:
        raise ValueError("time must be HH:MM")
    hour = int(hour_text)
    minute = int(minute_text)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("time must be a valid 24-hour clock value")
    return hour, minute


def catch_up_decision(
    *,
    enabled: bool,
    now_local: datetime,
    due_time: str,
    last_success_local: datetime | None,
    elapsed_guard_hours: int = 36,
) -> CatchUpDecision:
    """Decide whether a missed scheduled backup must be caught up.

    The rules follow BACKUP_STRATEGY.md §6.4:

    * Disabled scheduling never catches up.
    * With no successful automatic backup yet, catch up once.
    * After today's due time, catch up when the last success predates it.
    * Independently, catch up when more than ``elapsed_guard_hours`` elapsed.
    * A success after today's due time is never duplicated.
    """
    if not enabled:
        return CatchUpDecision(False, "automatic backups are disabled", due_time)

    hour, minute = parse_due_time(due_time)
    today_due = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if last_success_local is None:
        return CatchUpDecision(
            True,
            "no successful automatic backup is recorded",
            due_time,
            last_success_utc=None,
        )

    elapsed = now_local - last_success_local
    elapsed_hours = elapsed.total_seconds() / 3600

    if last_success_local >= today_due:
        return CatchUpDecision(
            False,
            "today's scheduled backup has already completed",
            due_time,
            last_success_utc=None,
            elapsed_hours=elapsed_hours,
        )

    if now_local >= today_due:
        return CatchUpDecision(
            True,
            "today's scheduled backup time has passed without a successful run",
            due_time,
            elapsed_hours=elapsed_hours,
        )

    if elapsed_guard_hours > 0 and elapsed >= timedelta(hours=elapsed_guard_hours):
        return CatchUpDecision(
            True,
            f"the last successful backup is older than {elapsed_guard_hours} hours",
            due_time,
            elapsed_hours=elapsed_hours,
        )

    return CatchUpDecision(
        False,
        "today's scheduled backup is not due yet",
        due_time,
        elapsed_hours=elapsed_hours,
    )


def select_retention_candidates(
    records: tuple[BackupRecord, ...] | list[BackupRecord],
    *,
    now_utc: datetime,
    retention_days: int,
    keep_minimum: int,
) -> tuple[BackupRecord, ...]:
    """Return automatic backups that are safe to delete.

    Safety rules enforced here:

    * Only verified automatic backups with a trustworthy timestamp qualify.
    * Manual and safety backups are never candidates.
    * The newest ``keep_minimum`` automatic backups are always retained.
    * The newest verified backup of any type is always retained.
    * At least one verified backup always survives.
    * Files with malformed, missing, or untrusted metadata are retained.
    """
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    if keep_minimum < 1:
        raise ValueError("keep_minimum must be at least 1")

    verified = [record for record in records if record.status is BackupStatus.VERIFIED]
    if not verified:
        return ()

    ordered = sorted(
        verified,
        key=lambda record: utc_sort_key(record.created_at_utc),
        reverse=True,
    )
    automatic = [
        record for record in ordered if record.backup_type is BackupType.AUTOMATIC
    ]
    newest_overall = ordered[0]
    protected_ids = {id(newest_overall)}
    protected_ids.update(id(record) for record in automatic[:keep_minimum])

    cutoff = now_utc - timedelta(days=retention_days)
    candidates: list[BackupRecord] = []
    for record in automatic:
        if id(record) in protected_ids:
            continue
        if record.created_at_utc is None:
            continue
        if record.created_at_utc >= cutoff:
            continue
        candidates.append(record)

    # Never let a plan empty the verified set, and never remove the newest
    # automatic backup that a replacement must supersede.
    remaining = len(verified) - len(candidates)
    if remaining < 1:
        candidates = candidates[: max(0, len(verified) - 1)]
    return tuple(candidates)


__all__ = [
    "BackupRecord",
    "BackupStatus",
    "BackupType",
    "CatchUpDecision",
    "catch_up_decision",
    "parse_due_time",
    "select_retention_candidates",
    "utc_sort_key",
]
