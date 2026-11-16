"""Startup catch-up for a missed automatic backup.

The policy is pure (:func:`app.domain.backup.catch_up_decision`). This service
only supplies the facts: the configured schedule, the last successful automatic
backup from durable state or history, and the current local time. It is
synchronous so the UI can run it in a background worker; nothing here touches Qt.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.core.config import ConfigService
from app.core.exceptions import BackupError, OperationLockedError
from app.domain.backup import BackupType, CatchUpDecision, catch_up_decision
from app.infrastructure.backup.history import BackupHistory
from app.infrastructure.backup.state import BackupStateStore
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CatchUpResult:
    """Whether a catch-up backup ran and what happened."""

    attempted: bool
    success: bool
    decision: CatchUpDecision
    message: str
    backup_file: str | None = None
    error: str | None = None


class CatchUpService:
    """Decide and (optionally) perform one startup catch-up backup."""

    def __init__(
        self,
        *,
        config_service: ConfigService,
        backup_service: BackupService,
        state_store: BackupStateStore,
        history: BackupHistory,
        clock: Callable[[], datetime] | None = None,
        app_version: str = "",
    ) -> None:
        self._config_service = config_service
        self._backup_service = backup_service
        self._state = state_store
        self._history = history
        self._clock = clock or (lambda: datetime.now().astimezone())
        self._app_version = app_version

    def evaluate(self) -> CatchUpDecision:
        """Return the current decision without starting a backup."""
        return self._decide()

    def run(self) -> CatchUpResult:
        """Perform a catch-up backup when the schedule says it is due."""
        decision = self._decide()
        if not decision.due:
            return CatchUpResult(
                attempted=False,
                success=False,
                decision=decision,
                message=decision.reason,
            )

        logger.info("Startup catch-up backup is due: %s", decision.reason)
        try:
            result = self._backup_service.create_backup(
                BackupType.AUTOMATIC,
                trigger="catch-up",
            )
        except OperationLockedError as exc:
            logger.info("Startup catch-up skipped because another operation holds the lock")
            return CatchUpResult(
                attempted=False,
                success=False,
                decision=decision,
                message=(
                    "Another backup, restore, or database move is running. The catch-up backup "
                    "will be retried later."
                ),
                error=str(exc),
            )
        except BackupError as exc:
            logger.warning("Startup catch-up backup failed: %s", exc)
            return CatchUpResult(
                attempted=True,
                success=False,
                decision=decision,
                message=exc.user_message,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - background task boundary
            logger.exception("Startup catch-up backup failed unexpectedly")
            return CatchUpResult(
                attempted=True,
                success=False,
                decision=decision,
                message=(
                    "The catch-up backup could not be created. See the application log for "
                    "details."
                ),
                error=str(exc),
            )

        logger.info("Startup catch-up backup completed: %s", result.path)
        return CatchUpResult(
            attempted=True,
            success=True,
            decision=decision,
            message=f"Catch-up backup created and verified: {result.record.file_name}",
            backup_file=result.record.file_name,
        )

    def _decide(self) -> CatchUpDecision:
        config = self._config_service.load()
        now_local = self._clock()
        last_success_local = self._last_success_local()
        return catch_up_decision(
            enabled=config.backup_enabled,
            now_local=now_local,
            due_time=config.backup_time,
            last_success_local=last_success_local,
        )

    def _last_success_local(self) -> datetime | None:
        state = self._state.read()
        if state.last_success_utc is not None:
            return state.last_success_utc.astimezone()
        latest = self._history.latest(BackupType.AUTOMATIC, verified_only=True)
        if latest is not None and latest.created_at_utc is not None:
            return latest.created_at_utc.astimezone()
        return None


__all__ = ["CatchUpResult", "CatchUpService"]
