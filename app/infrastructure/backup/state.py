"""Durable backup outcome state shared by the GUI and the headless runner.

The state file is advisory bookkeeping, never evidence that a backup is valid.
History is rebuilt from the managed directories and metadata sidecars; this file
only records the last successful and last failed attempt so the UI and the
startup catch-up can report them without scanning every backup.

A missing or malformed state file is treated as "no history" and is never a
reason to fail a backup or to block startup.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core import constants
from app.infrastructure.backup.metadata import BackupMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackupState:
    """The latest known outcome of each backup-related operation."""

    last_success_utc: datetime | None = None
    last_success_file: str | None = None
    last_success_type: str | None = None
    last_attempt_utc: datetime | None = None
    last_attempt_result: str | None = None
    last_failure_utc: datetime | None = None
    last_failure_message: str | None = None
    consecutive_failures: int = 0
    last_restore_utc: datetime | None = None
    last_restore_file: str | None = None
    last_relocation_utc: datetime | None = None
    last_relocation_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_version": constants.BACKUP_METADATA_VERSION,
            "last_success_utc": _format_optional(self.last_success_utc),
            "last_success_file": self.last_success_file,
            "last_success_type": self.last_success_type,
            "last_attempt_utc": _format_optional(self.last_attempt_utc),
            "last_attempt_result": self.last_attempt_result,
            "last_failure_utc": _format_optional(self.last_failure_utc),
            "last_failure_message": self.last_failure_message,
            "consecutive_failures": self.consecutive_failures,
            "last_restore_utc": _format_optional(self.last_restore_utc),
            "last_restore_file": self.last_restore_file,
            "last_relocation_utc": _format_optional(self.last_relocation_utc),
            "last_relocation_path": self.last_relocation_path,
        }

    @classmethod
    def from_dict(cls, data: Any) -> BackupState:
        if not isinstance(data, dict):
            raise ValueError("backup state root must be a JSON object")
        failures = data.get("consecutive_failures", 0)
        if isinstance(failures, bool) or not isinstance(failures, int) or failures < 0:
            failures = 0
        return cls(
            last_success_utc=_parse_optional(data.get("last_success_utc")),
            last_success_file=_optional_text(data.get("last_success_file")),
            last_success_type=_optional_text(data.get("last_success_type")),
            last_attempt_utc=_parse_optional(data.get("last_attempt_utc")),
            last_attempt_result=_optional_text(data.get("last_attempt_result")),
            last_failure_utc=_parse_optional(data.get("last_failure_utc")),
            last_failure_message=_optional_text(data.get("last_failure_message")),
            consecutive_failures=failures,
            last_restore_utc=_parse_optional(data.get("last_restore_utc")),
            last_restore_file=_optional_text(data.get("last_restore_file")),
            last_relocation_utc=_parse_optional(data.get("last_relocation_utc")),
            last_relocation_path=_optional_text(data.get("last_relocation_path")),
        )


class BackupStateStore:
    """Atomic read/write access to ``Backups\\backup_state.json``."""

    def __init__(self, path: Path, *, clock: datetime | None = None) -> None:
        self._path = Path(path)
        self._now = clock

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> BackupState:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return BackupState()
        try:
            return BackupState.from_dict(json.loads(raw))
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Backup state file is malformed and will be ignored: %s", self._path)
            return BackupState()

    def write(self, state: BackupState) -> None:
        """Atomically replace the state file, raising ``OSError`` on failure."""
        target = self._path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OSError(f"backup state folder could not be created: {target.parent}") from exc

        temp_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=".backup-state-", suffix=constants.BACKUP_TEMP_SUFFIX, dir=target.parent
            )
            temp_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(state.to_dict(), stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, target)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def record_success(self, metadata: BackupMetadata) -> BackupState:
        state = replace(
            self.read(),
            last_success_utc=metadata.created_at_utc,
            last_success_file=metadata.file_name,
            last_success_type=metadata.backup_type.value,
            last_attempt_utc=metadata.created_at_utc,
            last_attempt_result="success",
            consecutive_failures=0,
        )
        self._safe_write(state)
        return state

    def record_failure(self, message: str, *, when: datetime | None = None) -> BackupState:
        moment = when or self._now or datetime.now(UTC)
        current = self.read()
        state = replace(
            current,
            last_attempt_utc=moment,
            last_attempt_result="failed",
            last_failure_utc=moment,
            last_failure_message=message,
            consecutive_failures=current.consecutive_failures + 1,
        )
        self._safe_write(state)
        return state

    def record_restore(self, file_name: str, *, when: datetime | None = None) -> BackupState:
        moment = when or self._now or datetime.now(UTC)
        state = replace(
            self.read(),
            last_restore_utc=moment,
            last_restore_file=file_name,
        )
        self._safe_write(state)
        return state

    def record_relocation(self, database_path: str, *, when: datetime | None = None) -> BackupState:
        moment = when or self._now or datetime.now(UTC)
        state = replace(
            self.read(),
            last_relocation_utc=moment,
            last_relocation_path=database_path,
        )
        self._safe_write(state)
        return state

    def write_last_error(self, message: str, *, when: datetime | None = None) -> None:
        """Write a small diagnostic sidecar without touching valid history."""
        moment = when or self._now or datetime.now(UTC)
        target = self._path.with_name(constants.BACKUP_LAST_ERROR_FILENAME)
        payload = {
            "timestamp_utc": _format_optional(moment),
            "message": message,
        }
        temp_path: Path | None = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(
                prefix=".backup-error-", suffix=constants.BACKUP_TEMP_SUFFIX, dir=target.parent
            )
            temp_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, target)
            temp_path = None
        except OSError:
            logger.warning("Backup failure diagnostics could not be written: %s", target)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _safe_write(self, state: BackupState) -> None:
        try:
            self.write(state)
        except OSError:
            logger.warning("Backup state could not be saved: %s", self._path, exc_info=True)


def _format_optional(value: datetime | None) -> str | None:
    if value is None:
        return None
    moment = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_optional(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value


__all__ = ["BackupState", "BackupStateStore"]
