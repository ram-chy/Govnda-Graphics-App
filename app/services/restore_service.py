"""Application use case: restore a verified backup with staged replacement.

Restore never copies a live database. It first creates a verified safety backup
through the SQLite Online Backup API, closes every connection, prepares an
independent rollback snapshot, stages the selected backup on the destination
volume, carries forward audit events written since that backup, and replaces the
live file with an atomic rename. The reopened database must pass identity,
schema, integrity, foreign-key, audit-structure, and write checks before the
operation reports success.

If replacement or post-restore verification fails, the rollback snapshot is put
back and verified. If rollback itself fails, a recovery-required marker blocks
normal startup so the application never silently opens a damaged database.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core import constants
from app.core.config import ConfigService
from app.core.exceptions import RestoreError
from app.domain.backup import BackupRecord, BackupType
from app.domain.backup_assets import ManagedBackupAsset
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.hashing import sha256_file
from app.infrastructure.backup.history import BackupHistory
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.markers import (
    RECOVERY_REQUIRED_MARKER,
    RESTORE_MARKER,
    MarkerStore,
    OperationMarker,
    marker_paths,
)
from app.infrastructure.backup.metadata import BackupMetadata, MetadataError, read_metadata
from app.infrastructure.backup.naming import is_managed_backup_name, metadata_path_for
from app.infrastructure.backup.retention import clean_old_rollback_copies
from app.infrastructure.backup.snapshot import (
    DatabaseVerification,
    create_snapshot,
    fsync_directory,
    verify_database_file,
)
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.database.audit_history import (
    AuditHistorySummary,
    merge_audit_history,
    verify_audit_structure,
)
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import DatabaseDiagnostics
from app.infrastructure.database.migrations import verify_database_for_startup
from app.services.backup_service import BackupResult, BackupService, ProgressCallback
from app.services.database_runtime import DatabaseRuntime

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RestoreCandidate:
    """A backup that passed every eligibility check for a restore."""

    record: BackupRecord
    metadata: BackupMetadata
    verification: DatabaseVerification


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """The outcome of a verified restore."""

    restored_file: str
    database_path: Path
    safety_backup: BackupMetadata
    rollback_path: Path
    verification: DatabaseVerification
    duration_ms: int
    managed_assets_restored: int = 0
    audit_events_preserved: int = 0


class RestoreService:
    """Validate, stage, replace, verify, and roll back one database restore."""

    def __init__(
        self,
        *,
        config_service: ConfigService,
        runtime: DatabaseRuntime,
        directories: BackupDirectories,
        lock: OperationLock,
        backup_service: BackupService,
        expected_schema_revision: str,
        state_store: BackupStateStore | None = None,
        clock: Callable[[], datetime] | None = None,
        copier: Callable[[Path, Path], object] = shutil.copy2,
        replace_file: Callable[[Path, Path], object] = os.replace,
        verifier: Callable[[Path], DatabaseVerification] = verify_database_file,
        reopen: Callable[[Path], Database] | None = None,
    ) -> None:
        self._config_service = config_service
        self._runtime = runtime
        self._directories = directories
        self._lock = lock
        self._backup_service = backup_service
        self._expected_schema_revision = expected_schema_revision
        self._state = state_store or BackupStateStore(directories.state_path)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._copier = copier
        self._replace = replace_file
        self._verifier = verifier
        self._reopen = reopen or _reopen_and_verify
        self._history = BackupHistory(directories)

    def prepare(self, record: BackupRecord) -> RestoreCandidate:
        """Re-verify one history record; raise if it may not be restored."""
        path = Path(record.path)
        if not path.is_file():
            raise RestoreError(
                f"backup file is missing: {path}",
                user_message=(
                    "The selected backup file no longer exists. Refresh the history and choose "
                    "another backup."
                ),
            )
        if not self._directories.contains(path) or not is_managed_backup_name(path.name):
            raise RestoreError(
                f"backup is outside managed storage: {path}",
                user_message=(
                    "Only backups created by this application can be restored. Choose a backup "
                    "from the backup history."
                ),
            )

        metadata_path = metadata_path_for(path)
        if not metadata_path.is_file():
            raise RestoreError(
                f"backup has no metadata sidecar: {path}",
                user_message=(
                    "The selected backup has no verification record and cannot be restored."
                ),
            )
        try:
            metadata = read_metadata(metadata_path)
        except MetadataError as exc:
            raise RestoreError(
                f"backup metadata is invalid: {exc}",
                user_message=(
                    "The selected backup's verification record is invalid or unreadable. It "
                    "cannot be restored."
                ),
            ) from exc

        if metadata.file_name.lower() != path.name.lower():
            raise RestoreError(
                "backup metadata names a different file",
                user_message=(
                    "The selected backup does not match its verification record. It cannot be "
                    "restored."
                ),
            )
        if not metadata.verified:
            raise RestoreError(
                "backup metadata does not record a successful verification",
                user_message=(
                    "The selected backup was not verified successfully and cannot be restored."
                ),
            )
        if metadata.managed_assets:
            config = self._config_service.load()
            if config.data_root is None:
                raise RestoreError(
                    "backup contains managed assets but no data root is configured",
                    user_message=(
                        "This backup contains business logo files, but no business data folder "
                        "is configured. Set up or locate the business data before restoring."
                    ),
                )

        try:
            actual_size = path.stat().st_size
        except OSError as exc:
            raise RestoreError(
                f"backup size could not be read: {path}: {exc}",
                user_message="The selected backup file could not be read.",
            ) from exc
        if actual_size != metadata.backup_bytes:
            raise RestoreError(
                f"backup size changed: {actual_size} != {metadata.backup_bytes}",
                user_message=(
                    "The selected backup file changed after it was created. It cannot be "
                    "restored."
                ),
            )

        try:
            digest = sha256_file(path)
        except OSError as exc:
            raise RestoreError(
                f"backup checksum could not be calculated: {path}: {exc}",
                user_message="The selected backup file could not be read for verification.",
            ) from exc
        if digest != metadata.sha256:
            raise RestoreError(
                f"backup checksum does not match metadata: {path}",
                user_message=(
                    "The selected backup's checksum does not match its verification record. "
                    "The file may be damaged; it cannot be restored."
                ),
            )

        verification = self._verifier(path)
        if not verification.ok:
            raise RestoreError(
                f"backup failed integrity verification: {verification.failure_summary}",
                user_message=(
                    "The selected backup failed its integrity checks and cannot be restored: "
                    f"{verification.failure_summary}."
                ),
            )
        if verification.schema_revision != self._expected_schema_revision:
            raise RestoreError(
                f"backup schema revision {verification.schema_revision!r} is not supported by "
                f"this application ({self._expected_schema_revision!r})",
                user_message=(
                    "The selected backup uses a different database schema revision than this "
                    "application supports. It was not restored. Install the matching "
                    "application version or choose a compatible backup."
                ),
            )
        verify_audit_structure(path)

        if verification.application_id != metadata.application_id:
            raise RestoreError(
                "backup identity changed after verification",
                user_message=(
                    "The selected backup's application identity does not match its verification "
                    "record. It cannot be restored."
                ),
            )

        return RestoreCandidate(
            record=record,
            metadata=metadata,
            verification=verification,
        )

    def restore(
        self,
        candidate: RestoreCandidate,
        *,
        progress: ProgressCallback | None = None,
        assume_locked: bool = False,
    ) -> RestoreResult:
        """Replace the live database with a fully verified staged copy."""
        if assume_locked:
            return self._restore(candidate, progress=progress)
        with self._lock:
            return self._restore(candidate, progress=progress)

    def _restore(
        self,
        candidate: RestoreCandidate,
        *,
        progress: ProgressCallback | None,
    ) -> RestoreResult:
        started = self._clock()
        config = self._config_service.load()
        if config.database_path is None:
            raise RestoreError(
                "no database path is configured",
                user_message="No database location is configured, so there is nothing to restore.",
            )
        database_path = Path(config.database_path)
        marker = MarkerStore(marker_paths(database_path)[RESTORE_MARKER])
        staging_path = database_path.parent / constants.RESTORE_STAGING_FILENAME
        rollback_dir = database_path.parent / constants.ROLLBACK_DIR_NAME
        rollback_path: Path | None = None
        asset_staging: Path | None = None
        asset_rollback: Path | None = None
        asset_target: Path | None = None
        asset_source_existed = False
        assets_staged = False
        assets_replaced = False
        safety: BackupResult | None = None
        reopened: Database | None = None
        audit_summary = AuditHistorySummary(preserved=0, total=0)
        replacing = False
        closed = False

        try:
            self._report(progress, 0, "Preparing the restore")
            marker.write(
                OperationMarker(
                    operation=RESTORE_MARKER,
                    phase="starting",
                    started_at_utc=started,
                    database_path=str(database_path),
                    token=uuid.uuid4().hex,
                    detail=candidate.record.file_name,
                )
            )
            _require_healthy_current(database_path)

            self._report(progress, 8, "Creating a verified safety backup")
            safety = self._backup_service.create_backup(
                BackupType.SAFETY,
                trigger="restore",
                assume_locked=True,
                progress=_scaled(progress, 8, 45),
            )
            self._confirm_safety_backup(safety)

            staging_path.unlink(missing_ok=True)
            rollback_dir.mkdir(parents=True, exist_ok=True)
            rollback_path = _unique_rollback_path(rollback_dir)

            self._report(progress, 48, "Preparing a rollback copy")
            create_snapshot(database_path, rollback_path)
            rollback_check = self._verifier(rollback_path)
            if not rollback_check.ok:
                raise RestoreError(
                    f"rollback copy failed verification: {rollback_check.failure_summary}",
                    user_message=(
                        "A rollback copy of the current database could not be verified, so the "
                        "restore was stopped before replacing anything."
                    ),
                )

            if candidate.metadata.managed_assets:
                self._report(progress, 54, "Preparing managed profile files")
                asset_target = Path(config.data_root) / constants.DATA_LOGOS_DIR
                asset_staging = database_path.parent / constants.RESTORE_ASSETS_STAGING_DIR
                asset_rollback = rollback_dir / constants.RESTORE_ASSETS_ROLLBACK_DIR
                asset_source_existed = self._stage_managed_assets(
                    asset_staging,
                    asset_rollback,
                    asset_target,
                    candidate.metadata.managed_assets,
                )
                assets_staged = True

            self._report(progress, 56, "Staging the selected backup")
            self._copier(candidate.record.path, staging_path)
            staged = self._verifier(staging_path)
            if not staged.ok:
                raise RestoreError(
                    f"staged backup failed verification: {staged.failure_summary}",
                    user_message=(
                        "The staged restore copy failed verification. The current database was "
                        "not replaced."
                    ),
                )
            if staged.schema_revision != self._expected_schema_revision:
                raise RestoreError(
                    "staged backup has an unexpected schema revision",
                    user_message=(
                        "The staged restore copy has an unexpected schema revision. The current "
                        "database was not replaced."
                    ),
                )
            if sha256_file(staging_path) != candidate.metadata.sha256:
                raise RestoreError(
                    "staged backup checksum does not match",
                    user_message=(
                        "The staged restore copy failed its checksum check. The current database "
                        "was not replaced."
                    ),
                )

            marker.write(
                OperationMarker(
                    operation=RESTORE_MARKER,
                    phase="closing-database",
                    started_at_utc=started,
                    database_path=str(database_path),
                    detail=candidate.record.file_name,
                )
            )
            self._report(progress, 66, "Closing database connections")
            _checkpoint(database_path)
            self._runtime.close_and_dispose()
            closed = True
            _remove_sidecars(database_path)

            marker.write(
                OperationMarker(
                    operation=RESTORE_MARKER,
                    phase="preserving-audit-history",
                    started_at_utc=started,
                    database_path=str(database_path),
                    detail=candidate.record.file_name,
                )
            )
            self._report(progress, 70, "Preserving audit history")
            audit_summary = merge_audit_history(database_path, staging_path)
            merged = self._verifier(staging_path)
            if not merged.ok:
                raise RestoreError(
                    f"audit-preserved copy failed verification: {merged.failure_summary}",
                    user_message=(
                        "The restore copy failed verification after audit history was preserved. "
                        "The current database was not replaced."
                    ),
                )
            if merged.schema_revision != self._expected_schema_revision:
                raise RestoreError(
                    "audit-preserved copy has an unexpected schema revision",
                    user_message=(
                        "The restore copy changed schema revision after audit history was "
                        "preserved. The current database was not replaced."
                    ),
                )
            verify_audit_structure(staging_path)

            marker.write(
                OperationMarker(
                    operation=RESTORE_MARKER,
                    phase="replacing-database",
                    started_at_utc=started,
                    database_path=str(database_path),
                    detail=candidate.record.file_name,
                )
            )
            self._report(progress, 74, "Replacing the database")
            replacing = True
            self._replace(staging_path, database_path)
            _remove_sidecars(database_path)

            self._report(progress, 84, "Verifying the restored database")
            reopened = self._reopen(database_path)
            reopened_verification = verify_database_file(database_path, full=True)
            if not reopened_verification.ok:
                raise RestoreError(
                    f"restored database failed verification: "
                    f"{reopened_verification.failure_summary}",
                    user_message=(
                        "The restored database did not pass verification. The previous database "
                        "is being restored."
                    ),
                )

            if (
                assets_staged
                and asset_staging is not None
                and asset_target is not None
                and asset_rollback is not None
            ):
                marker.write(
                    OperationMarker(
                        operation=RESTORE_MARKER,
                        phase="replacing-managed-assets",
                        started_at_utc=started,
                        database_path=str(database_path),
                        detail=candidate.record.file_name,
                    )
                )
                self._report(progress, 88, "Replacing managed profile files")
                self._replace_managed_assets(
                    asset_staging, asset_target, asset_rollback, asset_source_existed
                )
                assets_replaced = True

            self._runtime.install(reopened)
            reopened = None
            marker.clear()
            self._state.record_restore(candidate.record.file_name, when=started)
            clean_old_rollback_copies(
                rollback_dir,
                retention_days=constants.ROLLBACK_RETENTION_DAYS,
            )
            elapsed = int((self._clock() - started).total_seconds() * 1000)
            logger.info(
                "Restore completed: %s -> %s in %d ms (safety backup %s)",
                candidate.record.file_name,
                database_path,
                elapsed,
                safety.metadata.file_name,
            )
            self._report(progress, 100, "Restore completed and verified")
            return RestoreResult(
                restored_file=candidate.record.file_name,
                database_path=database_path,
                safety_backup=safety.metadata,
                rollback_path=rollback_path,
                verification=reopened_verification,
                duration_ms=elapsed,
                managed_assets_restored=len(candidate.metadata.managed_assets),
                audit_events_preserved=audit_summary.preserved,
            )

        except Exception as exc:
            if reopened is not None:
                reopened.shutdown()
                reopened = None
            if closed:
                self._runtime.close()
            database_rolled_back = False
            asset_rolled_back = not assets_replaced
            rollback_error: Exception | None = None
            if (
                assets_replaced
                and asset_target is not None
                and asset_rollback is not None
            ):
                try:
                    self._report(progress, 90, "Rolling back managed profile files")
                    self._restore_managed_assets(
                        asset_target, asset_rollback, asset_source_existed
                    )
                except Exception as rollback_exc:  # noqa: BLE001 - recovery boundary
                    asset_rolled_back = False
                    rollback_error = rollback_exc
                    logger.critical("Managed asset rollback failed", exc_info=True)

            if replacing and rollback_path is not None and rollback_path.is_file():
                try:
                    self._report(progress, 92, "Rolling back the previous database")
                    _remove_sidecars(database_path)
                    self._replace(rollback_path, database_path)
                    _remove_sidecars(database_path)
                    recovered = self._reopen(database_path)
                    self._runtime.install(recovered)
                    marker.clear()
                    database_rolled_back = True
                    logger.warning("Restore failed and the previous database was restored")
                except Exception as rollback_exc:  # noqa: BLE001 - recovery boundary
                    rollback_error = rollback_error or rollback_exc
                    logger.critical("Restore rollback failed", exc_info=True)

            rolled_back = database_rolled_back and asset_rolled_back
            if asset_staging is not None and (not assets_replaced or asset_rolled_back):
                shutil.rmtree(asset_staging, ignore_errors=True)
            staging_path.unlink(missing_ok=True)
            if not rolled_back:
                if replacing:
                    _write_recovery_marker(database_path, marker, started, exc, rollback_error)
                else:
                    marker.clear()

            self._state.record_failure(
                f"restore failed: {exc}", when=started
            )
            self._state.write_last_error(f"restore failed: {exc}", when=started)
            logger.error("Restore failed: %s", exc, exc_info=True)
            if rolled_back:
                raise RestoreError(
                    f"restore failed and was rolled back: {exc}",
                    user_message=(
                        "The restore did not complete. The previous database was restored and "
                        "verified, and the safety backup was kept. No data was lost."
                    ),
                ) from exc
            raise RestoreError(
                f"restore and rollback failed: {exc}; rollback: {rollback_error}",
                user_message=(
                    "The restore did not complete and the previous database could not be "
                    "verified after rollback. The application will not open the database. "
                    "Use the recovery dialog or restore a safety backup from the backup "
                    "folder."
                ),
            ) from exc

    def _stage_managed_assets(
        self,
        staging_dir: Path,
        rollback_dir: Path,
        target_dir: Path,
        assets: tuple[ManagedBackupAsset, ...],
    ) -> bool:
        source_existed = target_dir.is_dir()
        shutil.rmtree(staging_dir, ignore_errors=True)
        shutil.rmtree(rollback_dir, ignore_errors=True)
        rollback_dir.mkdir(parents=True, exist_ok=True)
        if source_existed:
            shutil.copytree(target_dir, rollback_dir, dirs_exist_ok=True)
        try:
            for asset in assets:
                destination = staging_dir / asset.relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(asset.content)
                digest = sha256_file(destination)
                if destination.stat().st_size != asset.size_bytes or digest != asset.sha256:
                    raise RestoreError(
                        f"staged managed asset failed verification: {asset.relative_path}",
                        user_message=(
                            "A logo file in the backup did not pass verification. The current "
                            "database was not replaced."
                        ),
                    )
            if assets:
                fsync_directory(staging_dir)
        except OSError as exc:
            raise RestoreError(
                f"managed assets could not be staged: {exc}",
                user_message=(
                    "The logo files in the backup could not be staged. The current database was "
                    "not replaced."
                ),
            ) from exc
        return source_existed

    def _replace_managed_assets(
        self,
        staging_dir: Path,
        target_dir: Path,
        rollback_dir: Path,
        source_existed: bool,
    ) -> None:
        del rollback_dir, source_existed
        source = staging_dir / constants.DATA_LOGOS_DIR
        if not source.is_dir():
            raise RestoreError(
                f"staged managed asset folder is missing: {source}",
                user_message="The staged logo files could not be applied to the restored data.",
            )
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.is_dir():
            shutil.rmtree(target_dir)
        elif target_dir.exists():
            target_dir.unlink()
        shutil.move(str(source), str(target_dir))
        shutil.rmtree(staging_dir, ignore_errors=True)

    def _restore_managed_assets(
        self,
        target_dir: Path,
        rollback_dir: Path,
        source_existed: bool,
    ) -> None:
        if target_dir.is_dir():
            shutil.rmtree(target_dir)
        elif target_dir.exists():
            target_dir.unlink()
        if source_existed and rollback_dir.is_dir():
            shutil.move(str(rollback_dir), str(target_dir))

    def _confirm_safety_backup(self, result: BackupResult) -> None:
        verification = self._verifier(result.path)
        if not verification.ok:
            raise RestoreError(
                f"safety backup failed independent verification: {verification.failure_summary}",
                user_message=(
                    "The safety backup of the current database could not be verified, so the "
                    "restore was stopped before replacing anything."
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


def _require_healthy_current(database_path: Path) -> None:
    if not database_path.is_file():
        raise RestoreError(
            f"current database is missing: {database_path}",
            user_message=(
                f"The current database file is missing ({database_path}). Restore requires a "
                "healthy current database so a safety backup can be created."
            ),
        )
    verification = verify_database_file(database_path, full=False)
    if not verification.ok:
        raise RestoreError(
            f"current database failed preflight: {verification.failure_summary}",
            user_message=(
                "The current database did not pass its safety check, so it cannot be backed up "
                f"before restoring: {verification.failure_summary}."
            ),
        )


def _checkpoint(database_path: Path) -> None:
    """Best-effort WAL checkpoint through a direct short-lived connection."""
    import sqlite3

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(str(database_path), timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:
        logger.warning("WAL checkpoint before restore failed for %s", database_path, exc_info=True)
    finally:
        if connection is not None:
            connection.close()


def _remove_sidecars(database_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        candidate = database_path.with_name(f"{database_path.name}{suffix}")
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            logger.warning("SQLite sidecar could not be removed: %s", candidate)


def _unique_rollback_path(directory: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = directory / f"BusinessManagement_{timestamp}_ROLLBACK"
    candidate = base.with_suffix(".db")
    counter = 2
    while candidate.exists():
        candidate = directory / f"{base.name}_{counter}.db"
        counter += 1
    return candidate


def _reopen_and_verify(database_path: Path) -> Database:
    database = Database(DatabaseConfig(path=database_path))
    try:
        verify_database_for_startup(database)
        report = DatabaseDiagnostics(database).check(full=True)
        if not report.healthy:
            raise RestoreError(
                f"reopened database health check failed: {report.status.value}",
                user_message=(
                    "The restored database did not pass its health checks. The previous "
                    "database is being restored."
                ),
            )
    except BaseException:
        database.shutdown()
        raise
    return database


def _write_recovery_marker(
    database_path: Path,
    restore_marker: MarkerStore,
    started: datetime,
    failure: Exception,
    rollback_error: Exception | None,
) -> None:
    restore_marker.clear()
    path = marker_paths(database_path)[RECOVERY_REQUIRED_MARKER]
    detail = f"{failure}"
    if rollback_error is not None:
        detail = f"{detail}; rollback: {rollback_error}"
    try:
        MarkerStore(path).write(
            OperationMarker(
                operation=RECOVERY_REQUIRED_MARKER,
                phase="rollback-failed",
                started_at_utc=started,
                database_path=str(database_path),
                detail=detail[:2000],
            )
        )
    except OSError:
        logger.critical("Recovery-required marker could not be written: %s", path, exc_info=True)


__all__ = ["RestoreCandidate", "RestoreResult", "RestoreService"]
