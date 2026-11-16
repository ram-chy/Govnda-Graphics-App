"""In-progress and recovery-required marker files.

A destructive operation (restore, relocation, upgrade) connects a durable marker
next to the live database before it starts. If the process is killed halfway, the
next startup sees the marker and refuses to open the database silently. The
marker is advisory evidence, not a lock: the cross-process operation lock is the
exclusion mechanism.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core import constants

logger = logging.getLogger(__name__)

RECOVERY_REQUIRED_MARKER = "recovery_required"
RESTORE_MARKER = "restore"
RELOCATION_MARKER = "relocation"
UPGRADE_MARKER = "upgrade"


@dataclass(frozen=True, slots=True)
class OperationMarker:
    """The durable description of one interrupted protected operation."""

    operation: str
    phase: str
    started_at_utc: datetime
    database_path: str
    token: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker_version": constants.BACKUP_METADATA_VERSION,
            "operation": self.operation,
            "phase": self.phase,
            "started_at_utc": self.started_at_utc.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "database_path": self.database_path,
            "token": self.token,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: Any) -> OperationMarker:
        if not isinstance(data, dict):
            raise ValueError("operation marker root must be a JSON object")
        operation = data.get("operation")
        phase = data.get("phase")
        started = data.get("started_at_utc")
        database_path = data.get("database_path")
        if not isinstance(operation, str) or not operation:
            raise ValueError("operation marker has no operation")
        if not isinstance(phase, str) or not phase:
            raise ValueError("operation marker has no phase")
        if not isinstance(started, str) or not started:
            raise ValueError("operation marker has no timestamp")
        if not isinstance(database_path, str) or not database_path:
            raise ValueError("operation marker has no database path")
        text = started[:-1] + "+00:00" if started.endswith("Z") else started
        moment = datetime.fromisoformat(text)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return cls(
            operation=operation,
            phase=phase,
            started_at_utc=moment.astimezone(UTC),
            database_path=database_path,
            token=str(data.get("token") or ""),
            detail=str(data.get("detail") or ""),
        )

    def describe(self) -> str:
        return f"{self.operation} ({self.phase}) started {self.started_at_utc.isoformat()}"


class MarkerStore:
    """Read, write, and clear one marker file atomically."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.is_file()

    def read(self) -> OperationMarker | None:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            return OperationMarker.from_dict(json.loads(raw))
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Operation marker is malformed: %s", self._path)
            return None

    def write(self, marker: OperationMarker) -> None:
        target = self._path
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=".operation-marker-",
                suffix=constants.BACKUP_TEMP_SUFFIX,
                dir=target.parent,
            )
            temp_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(marker.to_dict(), stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, target)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def clear(self) -> None:
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Operation marker could not be removed: %s", self._path)


def marker_paths(database_path: Path) -> dict[str, Path]:
    """Return every marker path that belongs next to ``database_path``."""
    parent = Path(database_path).parent
    return {
        RESTORE_MARKER: parent / constants.RESTORE_MARKER_FILENAME,
        RELOCATION_MARKER: parent / constants.RELOCATION_MARKER_FILENAME,
        RECOVERY_REQUIRED_MARKER: parent / constants.RECOVERY_REQUIRED_MARKER_FILENAME,
        UPGRADE_MARKER: parent / ".upgrade-in-progress.json",
    }


def find_blocking_marker(database_path: Path) -> tuple[str, OperationMarker | None, Path] | None:
    """Return the first marker that must block normal startup.

    An unreadable marker file still blocks startup: corruption must never be
    treated as permission to open a possibly half-replaced database.
    """
    for kind, path in marker_paths(database_path).items():
        if not path.is_file():
            continue
        return kind, MarkerStore(path).read(), path
    return None


__all__ = [
    "MarkerStore",
    "OperationMarker",
    "RECOVERY_REQUIRED_MARKER",
    "RELOCATION_MARKER",
    "RESTORE_MARKER",
    "UPGRADE_MARKER",
    "find_blocking_marker",
    "marker_paths",
]
