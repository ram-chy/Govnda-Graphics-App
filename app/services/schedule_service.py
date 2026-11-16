"""Application use case: backup schedule settings and task registration.

Settings are persisted in the existing configuration file with an atomic write.
Windows Task Scheduler is updated before the configuration claims that automatic
backups are enabled, so a rejected registration is never reported as success. If
the configuration cannot be saved afterwards, the task change is undone.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.core.exceptions import ConfigurationError, SchedulerError
from app.infrastructure.backup.task_scheduler import (
    ScheduledTaskSpec,
    TaskQuery,
    WindowsTaskScheduler,
)

logger = logging.getLogger(__name__)

CommandParts = tuple[Path, str, Path]


@dataclass(frozen=True, slots=True)
class BackupSettings:
    """The user-visible schedule and retention settings."""

    enabled: bool
    time: str
    retention_days: int
    keep_minimum: int


@dataclass(frozen=True, slots=True)
class ScheduleUpdate:
    """The saved settings and the verified scheduler state."""

    settings: BackupSettings
    task_registered: bool
    message: str
    task: TaskQuery | None = None


def default_backup_command(config_path: Path) -> CommandParts:
    """Return ``(executable, arguments, working_directory)`` for the runner.

    A source checkout runs ``python -m app.tools.backup``. A frozen build runs
    the packaged executable with ``--run-backup`` so no development-only Python
    path can leak into a production task.
    """
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        arguments = f'--run-backup --scheduled --config "{config_path}"'
        working_directory = executable.parent
    else:
        arguments = f'-m app.tools.backup --scheduled --config "{config_path}"'
        working_directory = Path(__file__).resolve().parents[2]
    return executable, arguments, working_directory


class ScheduleService:
    """Read, validate, persist, and register the daily backup schedule."""

    def __init__(
        self,
        config_service: ConfigService,
        *,
        scheduler: WindowsTaskScheduler | None = None,
        command_builder: Callable[[Path], CommandParts] = default_backup_command,
        task_name: str = constants.SCHEDULED_TASK_NAME,
    ) -> None:
        self._config_service = config_service
        self._scheduler = scheduler or WindowsTaskScheduler()
        self._command_builder = command_builder
        self._task_name = task_name

    @property
    def task_name(self) -> str:
        return self._task_name

    @property
    def scheduler(self) -> WindowsTaskScheduler:
        return self._scheduler

    def settings(self) -> BackupSettings:
        config = self._config_service.load()
        return BackupSettings(
            enabled=config.backup_enabled,
            time=config.backup_time,
            retention_days=config.backup_retention_days,
            keep_minimum=config.backup_keep_minimum,
        )

    def task_status(self) -> TaskQuery:
        return self._scheduler.query(self._task_name)

    def build_spec(self, config: AppConfig | None = None) -> ScheduledTaskSpec:
        current = config or self._config_service.load()
        executable, arguments, working_directory = self._command_builder(
            self._config_service.config_path
        )
        return ScheduledTaskSpec(
            name=self._task_name,
            executable=executable,
            arguments=arguments,
            working_directory=working_directory,
            start_time=current.backup_time,
            description=constants.SCHEDULED_TASK_DESCRIPTION,
        )

    def update_settings(
        self,
        *,
        enabled: bool,
        time: str,
        retention_days: int,
        keep_minimum: int,
    ) -> ScheduleUpdate:
        """Validate, register/remove the task, then persist the settings."""
        original = self._config_service.load()
        try:
            updated = original.with_backup_settings(
                enabled=enabled,
                time=time,
                retention_days=retention_days,
                keep_minimum=keep_minimum,
            )
        except ConfigurationError:
            raise

        registered = False
        try:
            if updated.backup_enabled:
                status = self._scheduler.register(self.build_spec(updated))
                registered = status.exists
            else:
                self._scheduler.remove(self._task_name, ignore_missing=True)
        except SchedulerError:
            raise
        except Exception as exc:  # noqa: BLE001 - task failure must never look like success
            raise SchedulerError(
                f"automatic backup task could not be updated: {exc}",
                user_message=(
                    "Windows could not update the automatic backup task. The schedule was not "
                    "saved."
                ),
            ) from exc

        try:
            self._config_service.save(updated)
        except ConfigurationError:
            self._undo_task_change(original, registered)
            raise

        if updated.backup_enabled:
            message = (
                f"Automatic backups are enabled daily at {updated.backup_time} local time."
            )
        else:
            message = "Automatic backups are disabled."
        logger.info(
            "Backup schedule saved: enabled=%s time=%s retention=%s days keep=%s",
            updated.backup_enabled,
            updated.backup_time,
            updated.backup_retention_days,
            updated.backup_keep_minimum,
        )
        return ScheduleUpdate(
            settings=BackupSettings(
                enabled=updated.backup_enabled,
                time=updated.backup_time,
                retention_days=updated.backup_retention_days,
                keep_minimum=updated.backup_keep_minimum,
            ),
            task_registered=registered,
            message=message,
            task=self._scheduler.query(self._task_name),
        )

    def _undo_task_change(self, original: AppConfig, registered: bool) -> None:
        try:
            if registered:
                self._scheduler.remove(self._task_name, ignore_missing=True)
            elif original.backup_enabled:
                self._scheduler.register(self.build_spec(original))
        except Exception:  # noqa: BLE001 - best effort
            logger.critical(
                "The scheduled task could not be restored after a configuration failure",
                exc_info=True,
            )


__all__ = [
    "BackupSettings",
    "ScheduleService",
    "ScheduleUpdate",
    "default_backup_command",
]
