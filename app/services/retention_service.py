"""Application use case: apply the configured backup retention.

Retention runs only under the global operation lock so it can never delete a
backup that a restore or relocation is about to use. Selection is pure
(:func:`app.domain.backup.select_retention_candidates`); deletion is confined to
the managed directories by :class:`RetentionExecutor`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.history import BackupHistory
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.retention import RetentionExecutor, RetentionResult

logger = logging.getLogger(__name__)


class RetentionService:
    """Scan, select, and delete expired automatic backups under lock."""

    def __init__(
        self,
        *,
        directories: BackupDirectories,
        lock: OperationLock,
        history: BackupHistory | None = None,
        executor: RetentionExecutor | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._directories = directories
        self._lock = lock
        self._history = history or BackupHistory(directories)
        self._executor = executor or RetentionExecutor(directories)
        self._clock = clock or (lambda: datetime.now(UTC))

    def apply(
        self,
        *,
        retention_days: int,
        keep_minimum: int,
        assume_locked: bool = False,
    ) -> RetentionResult:
        """Apply retention and return what happened.

        A locked operation is reported as an :class:`OperationLockedError`; the
        caller decides whether that is an error or a harmless skip.
        """
        if assume_locked:
            return self._apply(retention_days=retention_days, keep_minimum=keep_minimum)
        with self._lock:
            return self._apply(retention_days=retention_days, keep_minimum=keep_minimum)

    def _apply(self, *, retention_days: int, keep_minimum: int) -> RetentionResult:
        scan = self._history.scan()
        result = self._executor.apply(
            scan.records,
            now_utc=self._clock(),
            retention_days=retention_days,
            keep_minimum=keep_minimum,
        )
        logger.info(
            "Retention complete: %d removed, %d retained, %d error(s)",
            len(result.deleted),
            result.retained,
            len(result.errors),
        )
        return result


__all__ = ["RetentionService"]
