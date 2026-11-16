"""Application use case: relocate the live database to another approved root.

Relocation is not a file copy. A verified safety backup is created first, then
the destination is produced with the SQLite Online Backup API and fully verified
before the configuration is updated. The old database and the old data root are
preserved; the user decides later whether to remove them.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import AppConfig, ConfigService
from app.core.exceptions import RelocationError
from app.domain.backup import BackupType
from app.infrastructure.backup.hashing import sha256_file
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.markers import (
    RELOCATION_MARKER,
    MarkerStore,
    OperationMarker,
    marker_paths,
)
from app.infrastructure.backup.metadata import BackupMetadata
from app.infrastructure.backup.naming import temp_path_for
from app.infrastructure.backup.snapshot import (
    DatabaseVerification,
    create_snapshot,
    verify_database_file,
    verify_writable,
)
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import DatabaseDiagnostics
from app.infrastructure.database.migrations import verify_database_for_startup
from app.infrastructure.filesystem.scaffold import DataRootScaffolder, ScaffoldResult
from app.infrastructure.filesystem.validation import (
    DataLocationValidator,
    LocationValidationResult,
)
from app.services.backup_service import BackupResult, BackupService, ProgressCallback
from app.services.database_runtime import DatabaseRuntime

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RelocationResult:
    """The verified outcome of moving the live database."""

    old_data_root: Path
    old_database_path: Path
    new_data_root: Path
    new_database_path: Path
    safety_backup: BackupMetadata
    schema_revision: str
    duration_ms: int


class RelocationService:
    """Move the live database without ever overwriting the only good copy."""

    def __init__(
        self,
        *,
        config_service: ConfigService,
        runtime: DatabaseRuntime,
        lock: OperationLock,
        backup_service: BackupService,
        validator: DataLocationValidator,
        state_store: BackupStateStore,
        scaffolder: DataRootScaffolder | None = None,
        clock: Callable[[], datetime] | None = None,
        replace_file: Callable[[Path, Path], object] = os.replace,
        verifier: Callable[[Path], DatabaseVerification] = verify_database_file,
        reopen: Callable[[Path], Database] | None = None,
    ) -> None:
        self._config_service = config_service
        self._runtime = runtime
        self._lock = lock
        self._backup_service = backup_service
        self._validator = validator
        self._state = state_store
        self._scaffolder = scaffolder or DataRootScaffolder()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._replace = replace_file
        self._verifier = verifier
        self._reopen = reopen or _open_and_verify

    def validate(self, data_root: str | Path | None) -> LocationValidationResult:
        return self._validator.validate(data_root)

    def relocate(
        self,
        data_root: str | Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> RelocationResult:
        with self._lock:
            return self._relocate(data_root, progress=progress)

    def _relocate(
        self,
        data_root: str | Path,
        *,
        progress: ProgressCallback | None,
    ) -> RelocationResult:
        started = self._clock()
        original = self._config_service.load()
        if original.data_root is None or original.database_path is None:
            raise RelocationError(
                "no database location is configured",
                user_message="Set up a database location before moving the database.",
            )
        old_root = Path(original.data_root)
        old_database = Path(original.database_path)

        validation = self._validator.validate(data_root)
        if not validation.is_valid or validation.layout is None:
            raise RelocationError(
                "destination data location is not valid",
                user_message=validation.error_summary,
            )
        layout = validation.layout
        new_root = layout.root
        new_database = layout.database_path

        if _same_path(new_root, old_root):
            raise RelocationError(
                "destination is the current data root",
                user_message=(
                    "The selected folder is already the current data location. Choose a "
                    "different folder."
                ),
            )
        if _same_path(new_database.parent, old_database.parent):
            raise RelocationError(
                "destination is the current database folder",
                user_message=(
                    "The selected folder would keep the database in its current folder. Choose "
                    "a different location."
                ),
            )
        if new_database.exists():
            raise RelocationError(
                f"destination already contains a database: {new_database}",
                user_message=(
                    f"The selected folder already contains a database ({new_database}). "
                    "Relocation never overwrites an existing database. Choose an empty folder."
                ),
            )
        if not old_database.is_file():
            raise RelocationError(
                f"current database is missing: {old_database}",
                user_message=(
                    f"The current database file does not exist ({old_database}). Nothing was "
                    "moved."
                ),
            )

        scaffold: ScaffoldResult | None = None
        new_database_engine: Database | None = None
        new_database_created = False
        temp_path: Path | None = None
        config_saved = False
        marker = MarkerStore(marker_paths(old_database)[RELOCATION_MARKER])
        try:
            marker.write(
                OperationMarker(
                    operation=RELOCATION_MARKER,
                    phase="starting",
                    started_at_utc=started,
                    database_path=str(old_database),
                    detail=str(layout.root),
                )
            )
            self._report(progress, 2, "Creating a verified safety backup")
            safety = self._backup_service.create_backup(
                BackupType.SAFETY,
                trigger="relocation",
                assume_locked=True,
                progress=_scaled(progress, 2, 35),
            )
            self._confirm_safety_backup(safety)

            self._report(progress, 38, "Preparing the destination folder")
            try:
                scaffold = self._scaffolder.create(layout)
            except Exception as exc:  # noqa: BLE001 - wrapped for the application boundary
                raise RelocationError(
                    f"destination folders could not be prepared: {exc}",
                    user_message=(
                        "The destination folders could not be prepared. Check the drive, free "
                        "space, and Windows permissions. The current database was not changed."
                    ),
                ) from exc

            self._report(progress, 46, "Copying the database to the destination")
            temp_path = temp_path_for(new_database)
            snapshot = create_snapshot(
                old_database,
                temp_path,
                progress=_scaled(progress, 46, 62),
            )

            self._report(progress, 64, "Verifying the destination database")
            destination_check = self._verifier(temp_path)
            if not destination_check.ok:
                raise RelocationError(
                    f"destination database failed verification: "
                    f"{destination_check.failure_summary}",
                    user_message=(
                        "The copy of the database at the new location did not pass verification. "
                        "The current database and settings were not changed."
                    ),
                )
            if destination_check.schema_revision is None:
                raise RelocationError(
                    "destination database has no schema revision",
                    user_message=(
                        "The copy of the database at the new location has no readable schema "
                        "revision. The current database and settings were not changed."
                    ),
                )
            destination_hash = sha256_file(temp_path)
            if destination_hash != snapshot.sha256:
                raise RelocationError(
                    "destination database checksum changed during verification",
                    user_message=(
                        "The copy of the database at the new location failed its checksum check. "
                        "The current database and settings were not changed."
                    ),
                )

            self._replace(temp_path, new_database)
            temp_path = None
            new_database_created = True
            marker.write(
                OperationMarker(
                    operation=RELOCATION_MARKER,
                    phase="verifying-destination",
                    started_at_utc=started,
                    database_path=str(old_database),
                    detail=str(new_database),
                )
            )
            writable, reason = verify_writable(new_database)
            if not writable:
                raise RelocationError(
                    f"destination database is not writable: {reason}",
                    user_message=(
                        "The database at the new location cannot be written to. Check the "
                        "folder's Windows permissions. The current database was not changed."
                    ),
                )

            self._report(progress, 72, "Opening the new database")
            new_database_engine = self._reopen(new_database)

            self._report(progress, 80, "Saving the new data location")
            marker.write(
                OperationMarker(
                    operation=RELOCATION_MARKER,
                    phase="saving-configuration",
                    started_at_utc=started,
                    database_path=str(old_database),
                    detail=str(new_database),
                )
            )
            updated = original.with_database_location(
                data_root=new_root,
                database_path=new_database,
            )
            self._config_service.save(updated)
            config_saved = True
            reloaded = self._config_service.load()
            self._verify_persisted(reloaded, new_root, new_database)

            self._report(progress, 90, "Switching the application to the new location")
            previous = self._runtime.install(new_database_engine)
            new_database_engine = None
            if previous is not None:
                previous.shutdown()

            self._state.record_relocation(str(new_database), when=started)
            marker.clear()
            elapsed = int((self._clock() - started).total_seconds() * 1000)
            logger.info(
                "Database relocated from %s to %s in %d ms; old copy preserved",
                old_database,
                new_database,
                elapsed,
            )
            self._report(progress, 100, "Database moved and verified")
            return RelocationResult(
                old_data_root=old_root,
                old_database_path=old_database,
                new_data_root=new_root,
                new_database_path=new_database,
                safety_backup=safety.metadata,
                schema_revision=destination_check.schema_revision,
                duration_ms=elapsed,
            )
        except Exception as exc:
            if new_database_engine is not None:
                new_database_engine.shutdown()
            if config_saved:
                try:
                    self._config_service.save(original)
                    logger.warning("Relocation failed; previous configuration restored")
                except Exception:  # noqa: BLE001 - best effort recovery
                    logger.critical(
                        "Relocation failed and the previous configuration could not be restored",
                        exc_info=True,
                    )
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            if new_database_created:
                new_database.unlink(missing_ok=True)
            if scaffold is not None:
                self._scaffolder.cleanup(scaffold)
            marker.clear()
            self._state.record_failure(
                f"relocation failed: {exc}", when=started
            )
            self._state.write_last_error(f"relocation failed: {exc}", when=started)
            logger.error("Relocation failed: %s", exc, exc_info=True)
            raise RelocationError(
                f"relocation failed: {exc}",
                user_message=(
                    "The database could not be moved. The current database and settings were "
                    "kept, and the old location remains usable."
                ),
            ) from exc

    def _confirm_safety_backup(self, result: BackupResult) -> None:
        verification = self._verifier(result.path)
        if not verification.ok:
            raise RelocationError(
                f"safety backup failed independent verification: {verification.failure_summary}",
                user_message=(
                    "The safety backup could not be verified, so the database was not moved."
                ),
            )

    @staticmethod
    def _verify_persisted(config: AppConfig, root: Path, database_path: Path) -> None:
        if config.data_root is None or not _same_path(Path(config.data_root), root):
            raise RelocationError(
                "saved data_root does not match the new location",
                user_message=(
                    "The settings file did not read back the new data folder. The current "
                    "database and settings are unchanged."
                ),
            )
        if config.database_path is None or not _same_path(
            Path(config.database_path), database_path
        ):
            raise RelocationError(
                "saved database_path does not match the new location",
                user_message=(
                    "The settings file did not read back the new database path. The current "
                    "database and settings are unchanged."
                ),
            )

    @staticmethod
    def _report(progress: ProgressCallback | None, percent: int, message: str) -> None:
        if progress is not None:
            progress(percent, message)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve(strict=False) == right.resolve(strict=False)
    except OSError:
        return str(left).casefold() == str(right).casefold()


def _scaled(progress: ProgressCallback | None, low: int, high: int) -> ProgressCallback | None:
    if progress is None:
        return None

    def report(percent: int, message: str) -> None:
        progress(low + int((high - low) * percent / 100), message)

    return report


def _open_and_verify(database_path: Path) -> Database:
    database = Database(DatabaseConfig(path=database_path))
    try:
        verify_database_for_startup(database)
        report = DatabaseDiagnostics(database).check(full=True)
        if not report.healthy:
            raise RelocationError(
                f"new database health check failed: {report.status.value}",
                user_message=(
                    "The database at the new location did not pass its health checks. The "
                    "current location remains in use."
                ),
            )
    except BaseException:
        database.shutdown()
        raise
    return database


__all__ = ["RelocationResult", "RelocationService"]
