"""Pre-upgrade safety-backup gate.

Every schema change that can touch existing data goes through this service. It
acquires the global operation lock, verifies the current database, creates and
independently re-verifies a Safety backup, and only then runs Alembic. A failed
backup stops the upgrade.

Normal application startup still never migrates automatically; the maintenance
tool is the only caller in Phase 4.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.exceptions import MigrationError, UpgradeError
from app.domain.backup import BackupType
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.markers import (
    UPGRADE_MARKER,
    MarkerStore,
    OperationMarker,
    marker_paths,
)
from app.infrastructure.backup.metadata import BackupMetadata
from app.infrastructure.backup.snapshot import verify_database_file
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import (
    MigrationManager,
    MigrationState,
    MigrationStatus,
)
from app.services.backup_service import BackupResult, BackupService, ProgressCallback

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpgradeResult:
    """A completed schema change and the safety backup that preceded it."""

    status: MigrationStatus
    safety_backup: BackupMetadata | None
    duration_ms: int


class UpgradeService:
    """Run a schema upgrade only after a verified Safety backup exists."""

    def __init__(
        self,
        *,
        directories: BackupDirectories,
        lock: OperationLock,
        backup_service: BackupService,
        state_store: BackupStateStore | None = None,
        migrations_dir: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._directories = directories
        self._lock = lock
        self._backup_service = backup_service
        self._state = state_store or BackupStateStore(directories.state_path)
        self._migrations_dir = migrations_dir
        self._clock = clock or (lambda: datetime.now(UTC))

    def upgrade(
        self,
        database: Database,
        target: str = "head",
        *,
        progress: ProgressCallback | None = None,
    ) -> UpgradeResult:
        return self._change(database, target=target, downgrade=False, progress=progress)

    def downgrade(
        self,
        database: Database,
        target: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> UpgradeResult:
        return self._change(database, target=target, downgrade=True, progress=progress)

    def _change(
        self,
        database: Database,
        *,
        target: str,
        downgrade: bool,
        progress: ProgressCallback | None,
    ) -> UpgradeResult:
        started = self._clock()
        manager = MigrationManager(database, self._migrations_dir)
        status = manager.status()

        if not downgrade and status.state is MigrationState.UP_TO_DATE:
            return UpgradeResult(status=status, safety_backup=None, duration_ms=0)
        if status.current_revision is None:
            raise UpgradeError(
                "the database has no schema revision to protect",
                user_message=(
                    "The database is not initialized, so a safety backup cannot protect it. "
                    "Create a new database with the initialization command instead."
                ),
            )
        if status.state is MigrationState.NEWER_SCHEMA:
            raise MigrationError(
                "the database schema is newer than this application",
                user_message=(
                    "The database was created by a newer application version. It will not be "
                    "changed."
                ),
            )

        with self._lock:
            self._report(progress, 2, "Verifying the current database")
            verification = verify_database_file(database.config.path, full=True)
            if not verification.ok:
                raise UpgradeError(
                    f"current database failed preflight: {verification.failure_summary}",
                    user_message=(
                        "The current database did not pass its safety check, so the schema "
                        f"change was not attempted: {verification.failure_summary}."
                    ),
                )

            self._report(progress, 8, "Creating a verified safety backup")
            safety = self._backup_service.create_backup(
                BackupType.SAFETY,
                trigger="upgrade",
                expected_schema_revision=status.current_revision,
                assume_locked=True,
                progress=_scaled(progress, 8, 70),
            )
            self._confirm_safety_backup(safety)

            self._report(progress, 78, "Applying the schema change")
            marker = MarkerStore(marker_paths(database.config.path)[UPGRADE_MARKER])
            marker.write(
                OperationMarker(
                    operation=UPGRADE_MARKER,
                    phase="applying-schema",
                    started_at_utc=started,
                    database_path=str(database.config.path),
                    detail=f"{status.current_revision} -> {target}",
                )
            )
            try:
                updated = (
                    manager.downgrade(target)
                    if downgrade
                    else manager.upgrade(target)
                )
            except Exception as exc:  # noqa: BLE001 - wrapped for the application boundary
                self._state.record_failure(f"schema change failed: {exc}", when=started)
                self._state.write_last_error(f"schema change failed: {exc}", when=started)
                raise UpgradeError(
                    f"schema change failed after the safety backup: {exc}",
                    user_message=(
                        "The database schema could not be changed. A verified safety backup was "
                        "created before the attempt. See the application log for details."
                    ),
                ) from exc

            marker.clear()
            elapsed = int((self._clock() - started).total_seconds() * 1000)
            logger.info(
                "Schema change completed: %s -> %s in %d ms (safety backup %s)",
                status.current_revision,
                updated.current_revision,
                elapsed,
                safety.metadata.file_name,
            )
            self._report(progress, 100, "Schema change completed")
            return UpgradeResult(
                status=updated,
                safety_backup=safety.metadata,
                duration_ms=elapsed,
            )

    def _confirm_safety_backup(self, result: BackupResult) -> None:
        verification = verify_database_file(result.path, full=True)
        if not verification.ok:
            raise UpgradeError(
                f"safety backup failed independent verification: {verification.failure_summary}",
                user_message=(
                    "The safety backup could not be verified, so the schema change was not "
                    "attempted."
                ),
            )

    @staticmethod
    def _report(progress: ProgressCallback | None, percent: int, message: str) -> None:
        if progress is not None:
            progress(percent, message)


def _scaled(progress: ProgressCallback | None, low: int, high: int) -> ProgressCallback | None:
    if progress is None:
        return None

    def report(percent: int, message: str) -> None:
        progress(low + int((high - low) * percent / 100), message)

    return report


__all__ = ["UpgradeResult", "UpgradeService"]
