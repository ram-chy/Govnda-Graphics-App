"""Application use case: create, verify, and publish one backup.

The sequence is deliberately linear and fails closed. A backup file and its JSON
sidecar appear in a managed directory only after the snapshot has passed an
independent full verification. Any failure removes the temporary file created by
this attempt and records the failure; the source database is never modified.

The caller may already hold the global operation lock (restore, relocation, and
upgrade create safety backups while holding it). ``assume_locked`` exists for
that case and must not be used by ordinary callers.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core import constants
from app.core.exceptions import BackupError, BackupVerificationError
from app.domain.backup import BackupRecord, BackupStatus, BackupType
from app.domain.backup_assets import ManagedBackupAsset
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.hashing import sha256_file
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.metadata import BackupMetadata, write_metadata_atomic
from app.infrastructure.backup.naming import (
    backup_paths,
    metadata_path_for,
    temp_path_for,
)
from app.infrastructure.backup.snapshot import (
    DatabaseVerification,
    SnapshotResult,
    clean_stale_temporary_files,
    create_snapshot,
    fsync_directory,
    verify_database_file,
)
from app.infrastructure.backup.state import BackupStateStore

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True, slots=True)
class BackupResult:
    """A published, independently verified backup."""

    metadata: BackupMetadata
    record: BackupRecord
    verification: DatabaseVerification
    snapshot: SnapshotResult
    duration_ms: int

    @property
    def path(self) -> Path:
        return self.record.path


class BackupService:
    """Create one verified backup at a time inside the managed storage tree."""

    def __init__(
        self,
        *,
        directories: BackupDirectories,
        database_path: Path,
        lock: OperationLock,
        state_store: BackupStateStore | None = None,
        app_version: str = constants.APP_VERSION,
        clock: Callable[[], datetime] | None = None,
        free_space_provider: Callable[[Path], int] | None = None,
        snapshotter: Callable[..., SnapshotResult] = create_snapshot,
        verifier: Callable[[Path], DatabaseVerification] = verify_database_file,
        source_verifier: Callable[[Path], DatabaseVerification] | None = None,
        hasher: Callable[[Path], str] = sha256_file,
        managed_asset_dirs: tuple[Path, ...] = (),
    ) -> None:
        self._directories = directories
        self._database_path = Path(database_path)
        self._lock = lock
        self._state = state_store or BackupStateStore(directories.state_path)
        self._app_version = app_version
        self._clock = clock or (lambda: datetime.now(UTC))
        self._free_space_provider = free_space_provider or _free_space
        self._snapshotter = snapshotter
        self._verifier = verifier
        self._source_verifier = source_verifier or (
            lambda path: verify_database_file(path, full=False)
        )
        self._hasher = hasher
        self._managed_asset_dirs = tuple(Path(path) for path in managed_asset_dirs)

    @property
    def directories(self) -> BackupDirectories:
        return self._directories

    @property
    def database_path(self) -> Path:
        return self._database_path

    @property
    def state_store(self) -> BackupStateStore:
        return self._state

    def create_backup(
        self,
        backup_type: BackupType,
        *,
        trigger: str,
        expected_schema_revision: str | None = None,
        assume_locked: bool = False,
        progress: ProgressCallback | None = None,
    ) -> BackupResult:
        """Create a verified backup or raise without publishing anything."""
        if assume_locked:
            return self._create(
                backup_type,
                trigger=trigger,
                expected_schema_revision=expected_schema_revision,
                progress=progress,
            )
        with self._lock:
            return self._create(
                backup_type,
                trigger=trigger,
                expected_schema_revision=expected_schema_revision,
                progress=progress,
            )

    def _create(
        self,
        backup_type: BackupType,
        *,
        trigger: str,
        expected_schema_revision: str | None,
        progress: ProgressCallback | None,
    ) -> BackupResult:
        started = self._clock()
        temp_path: Path | None = None
        final_path: Path | None = None
        published = False
        try:
            self._directories.ensure()
            destination_dir = self._directories.for_type(backup_type)
            self._report(progress, 1, "Checking the live database")
            source = self._validate_source()
            expected = expected_schema_revision or source.schema_revision
            if expected is None:
                raise BackupError(
                    f"the live database has no schema revision: {self._database_path}",
                    user_message=(
                        "The live database schema revision could not be read. Nothing was "
                        "backed up."
                    ),
                )

            managed_assets = self._collect_managed_assets()
            asset_bytes = sum(asset.size_bytes for asset in managed_assets)
            self._require_free_space(destination_dir, source.size_bytes + asset_bytes)
            clean_stale_temporary_files(destination_dir)

            created_local = started.astimezone()
            final_path, metadata_path = backup_paths(
                destination_dir, backup_type, created_local
            )
            temp_path = temp_path_for(final_path)
            logger.info(
                "Starting %s backup (%s) of %s to %s",
                backup_type.value,
                trigger,
                self._database_path,
                final_path.name,
            )

            self._report(progress, 5, "Copying a consistent SQLite snapshot")
            snapshot = self._snapshotter(
                self._database_path,
                temp_path,
                progress=_snapshot_progress(progress),
            )

            self._report(progress, 65, "Verifying the backup independently")
            verification = self._verifier(temp_path)
            if not verification.ok:
                raise BackupVerificationError(
                    f"backup verification failed for {temp_path.name}: "
                    f"{verification.failure_summary}",
                    user_message=(
                        "The backup did not pass verification and was not published: "
                        f"{verification.failure_summary}."
                    ),
                )
            if verification.schema_revision != expected:
                raise BackupVerificationError(
                    f"backup schema revision {verification.schema_revision!r} does not match "
                    f"the expected revision {expected!r}",
                    user_message=(
                        "The backup contains a different schema revision than expected and was "
                        "not published. No file was replaced."
                    ),
                )

            self._report(progress, 85, "Calculating the backup checksum")
            digest = self._hasher(temp_path)
            backup_bytes = snapshot.backup_bytes
            metadata = BackupMetadata(
                file_name=final_path.name,
                backup_type=backup_type,
                created_at_utc=started,
                app_version=self._app_version,
                application_id=int(verification.application_id or 0),
                schema_revision=verification.schema_revision or expected,
                source_database_path=str(self._database_path),
                source_database_bytes=source.size_bytes,
                backup_bytes=backup_bytes,
                sha256=digest,
                verification_result="verified",
                integrity_check=_result_text(verification.integrity_check),
                foreign_key_check=_result_text(verification.foreign_key_check),
                operation_result="success",
                duration_ms=int((self._clock() - started).total_seconds() * 1000),
                trigger=trigger,
                created_at_local=created_local.isoformat(),
                managed_assets=managed_assets,
            )

            self._report(progress, 95, "Publishing the verified backup")
            os.replace(temp_path, final_path)
            temp_path = None
            published = True
            fsync_directory(destination_dir)
            try:
                write_metadata_atomic(metadata_path, metadata)
            except BackupError:
                # A published database without valid metadata must not appear as
                # a successful backup. Remove only the file this attempt created.
                final_path.unlink(missing_ok=True)
                metadata_path_for(final_path).unlink(missing_ok=True)
                published = False
                raise

            record = BackupRecord(
                path=final_path,
                backup_type=backup_type,
                status=BackupStatus.VERIFIED,
                file_name=final_path.name,
                metadata_path=metadata_path,
                created_at_utc=metadata.created_at_utc,
                size_bytes=metadata.backup_bytes,
                schema_revision=metadata.schema_revision,
                verification_result=metadata.verification_result,
                detail="Created and verified by this application.",
            )
            self._state.record_success(metadata)
            elapsed = int((self._clock() - started).total_seconds() * 1000)
            logger.info(
                "Backup published: %s (%d bytes, %s) in %d ms",
                final_path,
                backup_bytes,
                digest[:12],
                elapsed,
            )
            self._report(progress, 100, "Backup completed and verified")
            return BackupResult(
                metadata=metadata,
                record=record,
                verification=verification,
                snapshot=snapshot,
                duration_ms=elapsed,
            )
        except Exception as exc:
            if not published:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
                # ``create_snapshot`` may already have removed the temp file.
                if final_path is not None and final_path.exists():
                    metadata_path_for(final_path).unlink(missing_ok=True)
                    final_path.unlink(missing_ok=True)
            message = exc.user_message if isinstance(exc, BackupError) else str(exc)
            self._state.record_failure(message, when=started)
            self._state.write_last_error(message, when=started)
            logger.error("Backup failed: %s", exc, exc_info=True)
            raise

    def _collect_managed_assets(self) -> tuple[ManagedBackupAsset, ...]:
        assets: list[ManagedBackupAsset] = []
        for root in self._managed_asset_dirs:
            if not root.exists():
                continue
            if not root.is_dir():
                raise BackupError(
                    f"managed asset path is not a folder: {root}",
                    user_message=(
                        "A managed profile-file path is damaged, so no backup was created."
                    ),
                )
            try:
                files = sorted(
                    path
                    for path in root.rglob("*")
                    if path.is_file() and not path.name.startswith(".")
                )
                for path in files:
                    content = path.read_bytes()
                    relative = f"{root.name}/{path.relative_to(root).as_posix()}"
                    assets.append(
                        ManagedBackupAsset(
                            relative_path=relative,
                            size_bytes=len(content),
                            sha256=hashlib.sha256(content).hexdigest(),
                            content=content,
                        )
                    )
            except OSError as exc:
                raise BackupError(
                    f"managed assets could not be read: {root}: {exc}",
                    user_message=(
                        "The managed profile files could not be read. No backup was created."
                    ),
                ) from exc
        return tuple(assets)

    def _validate_source(self) -> DatabaseVerification:
        source = self._database_path
        if not source.is_file():
            raise BackupError(
                f"live database is missing: {source}",
                user_message=(
                    f"The live database file does not exist ({source}). No backup was created. "
                    "Reconnect the drive or restore the data folder."
                ),
            )
        if source.stat().st_size <= 0:
            raise BackupError(
                f"live database is empty: {source}",
                user_message="The live database file is empty. No backup was created.",
            )
        verification = self._source_verifier(source)
        if not verification.ok:
            raise BackupError(
                f"live database failed preflight verification: {verification.failure_summary}",
                user_message=(
                    "The live database did not pass its safety check, so no backup was created: "
                    f"{verification.failure_summary}."
                ),
            )
        return verification

    def _require_free_space(self, directory: Path, source_bytes: int) -> None:
        required = (
            source_bytes * constants.BACKUP_FREE_SPACE_FACTOR_PERCENT // 100
            + constants.BACKUP_FREE_SPACE_RESERVE_BYTES
        )
        try:
            free = self._free_space_provider(directory)
        except OSError as exc:
            raise BackupError(
                f"free space could not be read for {directory}: {exc}",
                user_message=(
                    f"The backup folder could not be inspected ({directory}). Check that the "
                    "drive is connected."
                ),
            ) from exc
        if free < required:
            raise BackupError(
                f"insufficient free space in {directory}: {free} < {required}",
                user_message=(
                    "There is not enough free space to create a backup safely. Free space on "
                    "the backup drive or choose another location."
                ),
            )

    @staticmethod
    def _report(progress: ProgressCallback | None, percent: int, message: str) -> None:
        if progress is not None:
            progress(percent, message)


def _snapshot_progress(progress: ProgressCallback | None) -> Callable[[int, str], None] | None:
    if progress is None:
        return None

    def report(percent: int, message: str) -> None:
        progress(5 + int(percent * 0.55), message)

    return report


def _free_space(path: Path) -> int:
    return int(shutil.disk_usage(path).free)


def _result_text(messages: tuple[str, ...]) -> str:
    if not messages:
        return "ok"
    return "ok" if all(item.lower() == "ok" for item in messages) else "; ".join(messages)


__all__ = ["BackupResult", "BackupService", "ProgressCallback"]
