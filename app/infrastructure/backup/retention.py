"""Safe execution of the backup retention policy.

Policy selection is pure and lives in :mod:`app.domain.backup`. This module is
the only place that deletes backup files, and it re-checks every path against the
managed directories and the managed naming format before touching it. A deletion
failure is reported but never turns into a broader cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.core.exceptions import RetentionError
from app.domain.backup import BackupRecord, select_retention_candidates
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.naming import is_managed_backup_name, metadata_path_for
from app.infrastructure.backup.snapshot import clean_stale_temporary_files

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetentionResult:
    """What retention removed, kept, or could not remove."""

    deleted: tuple[Path, ...] = ()
    retained: int = 0
    errors: tuple[str, ...] = ()
    stale_temporary_files: tuple[Path, ...] = ()

    @property
    def failed(self) -> bool:
        return bool(self.errors)


class RetentionExecutor:
    """Delete only expired automatic backups that the policy marks safe."""

    def __init__(
        self,
        directories: BackupDirectories,
        *,
        remove_stale_temporary_files: bool = True,
    ) -> None:
        self._directories = directories
        self._remove_stale = remove_stale_temporary_files

    @property
    def directories(self) -> BackupDirectories:
        return self._directories

    def apply(
        self,
        records: tuple[BackupRecord, ...] | list[BackupRecord],
        *,
        now_utc: datetime,
        retention_days: int,
        keep_minimum: int,
    ) -> RetentionResult:
        try:
            candidates = select_retention_candidates(
                records,
                now_utc=now_utc,
                retention_days=retention_days,
                keep_minimum=keep_minimum,
            )
        except ValueError as exc:
            raise RetentionError(f"retention policy rejected its settings: {exc}") from exc

        removed: list[Path] = []
        errors: list[str] = []
        for record in candidates:
            if not self._is_deletable(record.path):
                logger.warning(
                    "Retention refused to delete a path outside managed backup storage: %s",
                    record.path,
                )
                errors.append(f"refused to delete unmanaged path: {record.path}")
                continue
            try:
                Path(record.path).unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Expired backup could not be deleted: %s (%s)", record.path, exc)
                errors.append(f"{record.file_name}: {exc}")
                continue
            removed.append(Path(record.path))
            metadata_path_for(record.path).unlink(missing_ok=True)
            logger.info(
                "Retention removed expired automatic backup %s (created %s)",
                record.file_name,
                record.created_at_utc.isoformat() if record.created_at_utc else "unknown",
            )

        stale: tuple[Path, ...] = ()
        if self._remove_stale:
            for directory in self._directories.managed:
                stale = (
                    *stale,
                    *clean_stale_temporary_files(directory),
                )

        return RetentionResult(
            deleted=tuple(removed),
            retained=len(records) - len(removed),
            errors=tuple(errors),
            stale_temporary_files=stale,
        )

    def _is_deletable(self, path: Path) -> bool:
        candidate = Path(path)
        if candidate.is_symlink():
            return False
        if not self._directories.contains(candidate):
            return False
        return is_managed_backup_name(candidate.name)


@dataclass(frozen=True, slots=True)
class RollbackCleanup:
    """Old rollback copies that were removed after a successful restore."""

    removed: tuple[Path, ...] = field(default_factory=tuple)


def clean_old_rollback_copies(
    directory: Path,
    *,
    retention_days: int,
    now_timestamp: float | None = None,
) -> tuple[Path, ...]:
    """Remove rollback copies older than the retention window.

    Only regular ``.db`` files inside the rollback directory are considered. An
    unreadable directory or file is retained.
    """
    import time

    folder = Path(directory)
    if not folder.is_dir():
        return ()
    cutoff = (time.time() if now_timestamp is None else now_timestamp) - retention_days * 86400
    removed: list[Path] = []
    try:
        entries = list(folder.iterdir())
    except OSError:
        return ()
    for entry in entries:
        if entry.is_symlink() or not entry.is_file() or entry.suffix.lower() != ".db":
            continue
        try:
            if entry.stat().st_mtime > cutoff:
                continue
            entry.unlink()
            removed.append(entry)
        except OSError:
            logger.warning("Old rollback copy could not be removed: %s", entry)
    if removed:
        logger.info("Removed %d old rollback cop(ies) from %s", len(removed), folder)
    return tuple(removed)


__all__ = ["RetentionExecutor", "RetentionResult", "clean_old_rollback_copies"]
