"""View model for the Backup screen.

The view model owns no widgets. It builds the backup workspace, submits jobs to a
background runner, and turns service results into signals. All safety decisions
(verification, locking, retention, restore order) remain in the application
services.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.core.config import ConfigService
from app.core.exceptions import AppError, BackupError
from app.domain.backup import BackupRecord, BackupStatus, BackupType
from app.infrastructure.backup.history import HistoryScan
from app.infrastructure.backup.state import BackupState
from app.infrastructure.filesystem.validation import LocationValidationResult
from app.services.backup_service import BackupResult
from app.services.backup_workspace import BackupWorkspace, BackupWorkspaceFactory
from app.services.catch_up_service import CatchUpResult
from app.services.database_runtime import DatabaseRuntime
from app.services.relocation_service import RelocationResult
from app.services.restore_service import RestoreResult
from app.services.schedule_service import BackupSettings, ScheduleUpdate
from app.ui.viewmodels.task_runner import (
    Job,
    TaskRunner,
    ThreadTaskRunner,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackupSnapshot:
    """Everything the Backup screen needs for one read-only render."""

    available: bool
    unavailable_reason: str
    data_root: Path | None
    database_path: Path | None
    records: tuple[BackupRecord, ...]
    state: BackupState
    settings: BackupSettings

    @property
    def verified(self) -> tuple[BackupRecord, ...]:
        return tuple(item for item in self.records if item.status is BackupStatus.VERIFIED)

    def latest_verified(self) -> BackupRecord | None:
        verified = self.verified
        return verified[0] if verified else None


class BackupViewModel(QObject):
    """Coordinates backup, restore, relocation, and schedule actions."""

    busy_changed = Signal(bool)
    progress_changed = Signal(int, str)
    snapshot_changed = Signal(object)
    status_message = Signal(str)
    operation_succeeded = Signal(str)
    operation_failed = Signal(str)
    database_changed = Signal(str, str)
    schedule_changed = Signal(object)

    def __init__(
        self,
        workspace_factory: BackupWorkspaceFactory,
        config_service: ConfigService,
        runtime: DatabaseRuntime,
        *,
        runner: TaskRunner | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._factory = workspace_factory
        self._config_service = config_service
        self._runtime = runtime
        self._runner: TaskRunner = runner or ThreadTaskRunner(self)
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def workspace(self) -> BackupWorkspace | None:
        return self._factory.build_optional()

    def refresh(self) -> None:
        """Re-read history and durable state without blocking the UI."""
        if self._busy:
            return
        self._busy = True
        self.busy_changed.emit(True)
        self.progress_changed.emit(0, "Reading backup history")

        def job(_progress) -> BackupSnapshot:
            return self._build_snapshot()

        self._runner.submit(
            job,
            on_progress=self.progress_changed.emit,
            on_success=self._on_snapshot,
            on_failure=self._on_read_failure,
        )

    def start_manual_backup(self) -> bool:
        workspace = self._workspace_or_report()
        if workspace is None:
            return False

        def job(progress) -> BackupResult:
            return workspace.backup_service.create_backup(
                backup_type=BackupType.MANUAL,
                trigger="manual",
                progress=progress,
            )

        def success(result: object) -> None:
            assert isinstance(result, BackupResult)
            self._finish()
            self.operation_succeeded.emit(
                f"Verified backup created: {result.record.file_name}"
            )
            self.refresh()

        return self._start("Creating a verified manual backup", job, success)

    def start_restore(self, record: BackupRecord) -> bool:
        workspace = self._workspace_or_report()
        if workspace is None:
            return False

        def job(progress) -> RestoreResult:
            progress(0, "Verifying the selected backup")
            candidate = workspace.restore_service.prepare(record)
            return workspace.restore_service.restore(candidate, progress=progress)

        def success(result: object) -> None:
            assert isinstance(result, RestoreResult)
            self._finish()
            self._emit_database_changed()
            self.operation_succeeded.emit(
                f"Restored {result.restored_file}. The previous database was kept as a "
                f"safety backup ({result.safety_backup.file_name})."
            )
            self.refresh()

        return self._start("Restoring the selected backup", job, success)

    def start_relocation(self, data_root: Path) -> bool:
        workspace = self._workspace_or_report()
        if workspace is None:
            return False

        def job(progress) -> RelocationResult:
            return workspace.relocation_service.relocate(data_root, progress=progress)

        def success(result: object) -> None:
            assert isinstance(result, RelocationResult)
            self._finish()
            self._emit_database_changed()
            self.operation_succeeded.emit(
                f"Database moved to {result.new_database_path}. The old copy was preserved "
                f"at {result.old_database_path}."
            )
            self.refresh()

        return self._start("Moving the database", job, success)

    def validate_relocation(self, data_root: Path) -> LocationValidationResult | None:
        workspace = self.workspace
        if workspace is None:
            self.operation_failed.emit(
                "Backups are unavailable because no business data folder is recorded."
            )
            return None
        return workspace.relocation_service.validate(data_root)

    def start_schedule_update(
        self,
        *,
        enabled: bool,
        time: str,
        retention_days: int,
        keep_minimum: int,
    ) -> bool:
        workspace = self._workspace_or_report()
        if workspace is None:
            return False

        def job(_progress) -> ScheduleUpdate:
            return workspace.schedule_service.update_settings(
                enabled=enabled,
                time=time,
                retention_days=retention_days,
                keep_minimum=keep_minimum,
            )

        def success(result: object) -> None:
            assert isinstance(result, ScheduleUpdate)
            self._finish()
            self.schedule_changed.emit(result)
            self.operation_succeeded.emit(result.message)
            self.refresh()

        return self._start("Saving the backup schedule", job, success)

    def run_startup_catch_up(self) -> bool:
        """Run one catch-up check in the background; never opens a dialog."""
        if self._busy:
            return False
        workspace = self.workspace
        if workspace is None:
            return False

        def job(_progress) -> CatchUpResult:
            return workspace.catch_up_service.run()

        def success(result: object) -> None:
            assert isinstance(result, CatchUpResult)
            self._finish()
            if result.attempted and result.success:
                self.status_message.emit(result.message)
                self.refresh()
            elif result.attempted:
                self.status_message.emit(
                    "The catch-up backup did not complete. See the backup screen for details."
                )
                self.refresh()

        return self._start("Checking for a missed automatic backup", job, success)

    def task_status_text(self) -> str:
        workspace = self.workspace
        if workspace is None:
            return "Automatic backups are unavailable."
        try:
            status = workspace.schedule_service.task_status()
        except AppError as exc:
            return f"Task status unavailable: {exc.user_message}"
        if not workspace.schedule_service.scheduler.supported:
            return "Windows Task Scheduler is not available on this system."
        if not status.exists:
            return "The Windows backup task is not registered."
        return "The Windows backup task is registered."

    def shutdown(self) -> None:
        if isinstance(self._runner, ThreadTaskRunner):
            self._runner.wait_for_done()

    # -- internals ---------------------------------------------------------

    def _workspace_or_report(self) -> BackupWorkspace | None:
        workspace = self.workspace
        if workspace is None:
            self.operation_failed.emit(
                "Backups are unavailable because the settings do not record a business "
                "data folder. Complete setup or locate the existing business data first."
            )
        return workspace

    def _start(self, label: str, job: Job, success) -> bool:
        if self._busy:
            self.status_message.emit("Another backup operation is already running.")
            return False
        self._busy = True
        self.busy_changed.emit(True)
        self.progress_changed.emit(0, label)

        def on_success(result: object) -> None:
            try:
                success(result)
            except Exception:  # noqa: BLE001 - presentation boundary
                logger.exception("Backup operation result could not be handled")
                self._finish()
                self.operation_failed.emit(
                    "The operation finished but its result could not be displayed. See the "
                    "application log."
                )

        self._runner.submit(
            job,
            on_progress=self.progress_changed.emit,
            on_success=on_success,
            on_failure=self._on_operation_failure,
        )
        return True

    def _on_operation_failure(self, user_message: str, detail: str) -> None:
        logger.info("Backup operation failed: %s", detail)
        self._finish()
        self.operation_failed.emit(user_message)
        self.refresh()

    def _on_read_failure(self, user_message: str, detail: str) -> None:
        logger.warning("Backup history could not be read: %s (%s)", user_message, detail)
        self._finish()
        self.operation_failed.emit(user_message)

    def _finish(self) -> None:
        if self._busy:
            self._busy = False
            self.busy_changed.emit(False)

    def _on_snapshot(self, snapshot: object) -> None:
        assert isinstance(snapshot, BackupSnapshot)
        self._finish()
        self.snapshot_changed.emit(snapshot)

    def _build_snapshot(self) -> BackupSnapshot:
        config = self._config_service.load()
        settings = BackupSettings(
            enabled=config.backup_enabled,
            time=config.backup_time,
            retention_days=config.backup_retention_days,
            keep_minimum=config.backup_keep_minimum,
        )
        try:
            workspace = self._factory.build(config)
        except BackupError as exc:
            return BackupSnapshot(
                available=False,
                unavailable_reason=exc.user_message,
                data_root=Path(config.data_root) if config.data_root else None,
                database_path=Path(config.database_path) if config.database_path else None,
                records=(),
                state=BackupState(),
                settings=settings,
            )

        scan: HistoryScan = workspace.history.scan()
        return BackupSnapshot(
            available=True,
            unavailable_reason="",
            data_root=workspace.data_root,
            database_path=workspace.database_path,
            records=scan.records,
            state=workspace.state_store.read(),
            settings=settings,
        )

    def _emit_database_changed(self) -> None:
        config = self._config_service.load()
        if config.data_root is None or config.database_path is None:
            return
        self.database_changed.emit(config.data_root, config.database_path)


__all__ = ["BackupSnapshot", "BackupViewModel"]
