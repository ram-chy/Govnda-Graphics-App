"""Composition of the backup, restore, relocation, and schedule use cases.

The GUI, the headless runner, and the maintenance tools must build the same
object graph with the same safety rules. This module is that single factory. It
is entirely Qt-free: the presentation layer receives a workspace and calls it
from a background worker.

A workspace is bound to one configured data root. After relocation the caller
asks the factory to build a new workspace; nothing is mutated in place, so a
stale directory path can never survive a move.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.core.exceptions import BackupError
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.history import BackupHistory
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.backup.task_scheduler import WindowsTaskScheduler
from app.infrastructure.database.migrations import (
    application_head_revision,
    default_migrations_dir,
)
from app.infrastructure.filesystem.layout import DataRootLayout
from app.infrastructure.filesystem.validation import DataLocationValidator
from app.services.backup_service import BackupService
from app.services.catch_up_service import CatchUpService
from app.services.database_runtime import DatabaseRuntime
from app.services.relocation_service import RelocationService
from app.services.restore_service import RestoreService
from app.services.retention_service import RetentionService
from app.services.schedule_service import ScheduleService
from app.services.upgrade_service import UpgradeService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackupWorkspace:
    """All backup-related use cases bound to one configured data root."""

    config: AppConfig
    layout: DataRootLayout
    directories: BackupDirectories
    history: BackupHistory
    state_store: BackupStateStore
    expected_schema_revision: str
    backup_service: BackupService
    retention_service: RetentionService
    restore_service: RestoreService
    relocation_service: RelocationService
    upgrade_service: UpgradeService
    schedule_service: ScheduleService
    catch_up_service: CatchUpService

    @property
    def data_root(self) -> Path:
        return self.layout.root

    @property
    def database_path(self) -> Path:
        return self.layout.database_path


class BackupWorkspaceFactory:
    """Build a :class:`BackupWorkspace` for the current configuration.

    The factory is cheap to keep for the whole session. Restore and relocation
    replace the live database, so the caller rebuilds the workspace from the
    configuration that the operation persisted rather than reusing stale paths.
    """

    def __init__(
        self,
        config_service: ConfigService,
        runtime: DatabaseRuntime,
        *,
        validator: DataLocationValidator | None = None,
        scheduler: WindowsTaskScheduler | None = None,
        migrations_dir: Path | None = None,
        app_version: str = constants.APP_VERSION,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config_service = config_service
        self._runtime = runtime
        self._validator = validator or DataLocationValidator()
        self._scheduler = scheduler or WindowsTaskScheduler()
        self._migrations_dir = migrations_dir
        self._app_version = app_version
        self._clock = clock
        self._head: str | None = None

    @property
    def config_service(self) -> ConfigService:
        return self._config_service

    @property
    def runtime(self) -> DatabaseRuntime:
        return self._runtime

    @property
    def validator(self) -> DataLocationValidator:
        return self._validator

    def build(self, config: AppConfig | None = None) -> BackupWorkspace:
        """Return the workspace or raise a user-facing configuration error."""
        current = config if config is not None else self._config_service.load()
        layout = layout_for_config(current)
        if layout is None:
            raise BackupError(
                "the configuration does not describe a backup-capable data root",
                user_message=(
                    "Backups are unavailable because the settings do not record a business "
                    "data folder. Complete setup or locate the existing business data first."
                ),
            )

        directories = BackupDirectories.from_layout(layout)
        history = BackupHistory(directories)
        state_store = BackupStateStore(directories.state_path)
        expected = self._expected_revision()

        backup_service = BackupService(
            directories=directories,
            database_path=layout.database_path,
            lock=OperationLock(directories.lock_path, operation="backup"),
            state_store=state_store,
            app_version=self._app_version,
            clock=self._clock,
        )
        retention_service = RetentionService(
            directories=directories,
            lock=OperationLock(directories.lock_path, operation="retention"),
            history=history,
            clock=self._clock,
        )
        restore_service = RestoreService(
            config_service=self._config_service,
            runtime=self._runtime,
            directories=directories,
            lock=OperationLock(directories.lock_path, operation="restore"),
            backup_service=backup_service,
            expected_schema_revision=expected,
            state_store=state_store,
            clock=self._clock,
        )
        relocation_service = RelocationService(
            config_service=self._config_service,
            runtime=self._runtime,
            lock=OperationLock(directories.lock_path, operation="relocation"),
            backup_service=backup_service,
            validator=self._validator,
            state_store=state_store,
            clock=self._clock,
        )
        upgrade_service = UpgradeService(
            directories=directories,
            lock=OperationLock(directories.lock_path, operation="upgrade"),
            backup_service=backup_service,
            state_store=state_store,
            migrations_dir=self._migrations_dir,
            clock=self._clock,
        )
        schedule_service = ScheduleService(
            self._config_service,
            scheduler=self._scheduler,
        )
        catch_up_service = CatchUpService(
            config_service=self._config_service,
            backup_service=backup_service,
            state_store=state_store,
            history=history,
            clock=self._clock,
            app_version=self._app_version,
        )

        logger.debug("Backup workspace built for %s", layout.root)
        return BackupWorkspace(
            config=current,
            layout=layout,
            directories=directories,
            history=history,
            state_store=state_store,
            expected_schema_revision=expected,
            backup_service=backup_service,
            retention_service=retention_service,
            restore_service=restore_service,
            relocation_service=relocation_service,
            upgrade_service=upgrade_service,
            schedule_service=schedule_service,
            catch_up_service=catch_up_service,
        )

    def build_optional(self) -> BackupWorkspace | None:
        """Return ``None`` when the configuration lacks a usable data root."""
        try:
            return self.build()
        except BackupError:
            logger.info("Backup workspace is unavailable for the current configuration")
            return None

    def _expected_revision(self) -> str:
        if self._head is None:
            self._head = application_head_revision(
                self._migrations_dir or default_migrations_dir()
            )
        return self._head


def layout_for_config(config: AppConfig) -> DataRootLayout | None:
    """Return the approved layout for a configuration, or ``None``.

    A legacy configuration may record only ``database_path``. The application
    must not guess a backup root from it, so such a configuration has no
    workspace until the user completes setup or recovery.
    """
    if config.data_root is None or config.database_path is None:
        return None
    try:
        layout = DataRootLayout(Path(config.data_root))
    except ValueError:
        return None
    if not _same_path(layout.database_path, Path(config.database_path)):
        return None
    return layout


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve(strict=False) == right.resolve(strict=False)
    except OSError:
        return str(left).casefold() == str(right).casefold()


__all__ = ["BackupWorkspace", "BackupWorkspaceFactory", "layout_for_config"]
