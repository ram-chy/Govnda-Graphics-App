"""Preserve immutable audit history across verified database replacement.

Restore replaces the live SQLite file with an older backup. Because audit events
are retained indefinitely, any event written after the backup was created must
be carried forward into the staged copy before it replaces the live database.
Only INSERT statements are used here; existing events are never updated,
deleted, or renumbered.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import RestoreError

AUDIT_TABLE = "audit_events"
AUDIT_UPDATE_TRIGGER = "trg_audit_events_no_update"
AUDIT_DELETE_TRIGGER = "trg_audit_events_no_delete"
_REQUIRED_TRIGGERS = (AUDIT_UPDATE_TRIGGER, AUDIT_DELETE_TRIGGER)
_COLUMNS = (
    "event_type",
    "entity_type",
    "entity_id",
    "actor",
    "created_at",
    "payload",
)


@dataclass(frozen=True, slots=True)
class AuditEventRow:
    """One immutable audit row copied between database files."""

    id: int
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    created_at: str
    payload: str

    @property
    def fingerprint(self) -> tuple[str, ...]:
        return (
            self.event_type,
            self.entity_type,
            self.entity_id,
            self.actor,
            self.created_at,
            self.payload,
        )


@dataclass(frozen=True, slots=True)
class AuditHistorySummary:
    """Result of carrying current audit events into a staged database."""

    preserved: int
    total: int


def verify_audit_structure(path: Path) -> None:
    """Refuse a database whose audit table or immutability triggers are absent."""
    if not path.is_file():
        raise RestoreError(
            f"audit structure check failed: database is missing: {path}",
            user_message="The database needed for this operation is missing. Nothing was changed.",
        )
    try:
        with closing(_connect(path)) as connection, connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (AUDIT_TABLE,),
            ).fetchone()
            if table is None:
                raise RestoreError(
                    f"audit structure check failed: {path} has no {AUDIT_TABLE} table",
                    user_message=(
                        "The database has no audit history table, so audit records cannot be "
                        "preserved. The operation was stopped."
                    ),
                )
            columns = {
                str(row[1])
                for row in connection.execute(f"PRAGMA table_info({AUDIT_TABLE})").fetchall()
            }
            missing_columns = set(_COLUMNS) - columns
            if missing_columns:
                raise RestoreError(
                    f"audit structure check failed: missing columns {sorted(missing_columns)}",
                    user_message=(
                        "The database audit table is incomplete, so audit records cannot be "
                        "preserved. The operation was stopped."
                    ),
                )
            triggers = _trigger_names(connection)
            missing_triggers = set(_REQUIRED_TRIGGERS) - triggers
            if missing_triggers:
                raise RestoreError(
                    f"audit structure check failed: missing triggers {sorted(missing_triggers)}",
                    user_message=(
                        "The database does not enforce append-only audit history, so it cannot "
                        "be used for this operation."
                    ),
                )
    except sqlite3.Error as exc:
        raise RestoreError(
            f"audit structure check failed for {path}: {exc}",
            user_message="The database audit structure could not be verified. Nothing was changed.",
        ) from exc


def read_audit_rows(path: Path) -> tuple[AuditEventRow, ...]:
    """Read audit rows from a database file without changing it."""
    verify_audit_structure(path)
    try:
        with closing(_connect(path)) as connection, connection:
            rows = connection.execute(
                "SELECT id, event_type, entity_type, entity_id, actor, created_at, payload "
                f"FROM {AUDIT_TABLE} ORDER BY id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise RestoreError(
            f"audit history could not be read from {path}: {exc}",
            user_message="Audit history could not be read. The operation was stopped.",
        ) from exc
    return tuple(
        AuditEventRow(
            id=int(row[0]),
            event_type=str(row[1]),
            entity_type=str(row[2]),
            entity_id=str(row[3]),
            actor=str(row[4]),
            created_at=str(row[5]),
            payload=str(row[6]),
        )
        for row in rows
    )


def merge_audit_history(source: Path, target: Path) -> AuditHistorySummary:
    """Copy audit events present in ``source`` but missing from ``target``.

    Rows with a matching fingerprint are already preserved. A colliding ID with
    different content is never overwritten; the missing event is appended with
    a new, unused ID so no historical fact is discarded.
    """
    source_rows = read_audit_rows(source)
    verify_audit_structure(target)
    try:
        with closing(_connect(target)) as connection, connection:
            target_rows = connection.execute(
                "SELECT id, event_type, entity_type, entity_id, actor, created_at, payload "
                f"FROM {AUDIT_TABLE} ORDER BY id"
            ).fetchall()
            fingerprints = {
                (
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    str(row[4]),
                    str(row[5]),
                    str(row[6]),
                )
                for row in target_rows
            }
            used_ids = {int(row[0]) for row in target_rows}
            next_id = max(used_ids, default=0) + 1
            appended = 0
            for row in source_rows:
                if row.fingerprint in fingerprints:
                    continue
                while next_id in used_ids:
                    next_id += 1
                connection.execute(
                    "INSERT INTO "
                    f"{AUDIT_TABLE} "
                    "(id, event_type, entity_type, entity_id, actor, created_at, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        next_id,
                        row.event_type,
                        row.entity_type,
                        row.entity_id,
                        row.actor,
                        row.created_at,
                        row.payload,
                    ),
                )
                used_ids.add(next_id)
                fingerprints.add(row.fingerprint)
                appended += 1
                next_id += 1
    except sqlite3.Error as exc:
        raise RestoreError(
            f"audit history could not be preserved in {target}: {exc}",
            user_message=(
                "Audit history could not be carried into the restore copy. The current "
                "database was not replaced."
            ),
        ) from exc
    return AuditHistorySummary(preserved=appended, total=len(source_rows))


def _trigger_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = ?",
        (AUDIT_TABLE,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


__all__ = [
    "AUDIT_DELETE_TRIGGER",
    "AUDIT_TABLE",
    "AUDIT_UPDATE_TRIGGER",
    "AuditEventRow",
    "AuditHistorySummary",
    "merge_audit_history",
    "read_audit_rows",
    "verify_audit_structure",
]
