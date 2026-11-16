"""Backup history discovered from managed directories and sidecar metadata.

History is a filesystem view, not proof of current validity. A record is marked
``VERIFIED`` only when its sidecar is valid and consistent with the file on disk;
restore still performs a fresh checksum and integrity verification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core import constants
from app.domain.backup import BackupRecord, BackupStatus, BackupType, utc_sort_key
from app.infrastructure.backup.directories import BackupDirectories
from app.infrastructure.backup.metadata import BackupMetadata, MetadataError, read_metadata
from app.infrastructure.backup.naming import is_managed_backup_name, metadata_path_for

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HistoryScan:
    """Immutable result of scanning the three managed backup directories."""

    records: tuple[BackupRecord, ...]

    @property
    def verified(self) -> tuple[BackupRecord, ...]:
        return tuple(item for item in self.records if item.status is BackupStatus.VERIFIED)

    def latest(
        self,
        backup_type: BackupType | None = None,
        *,
        verified_only: bool = False,
    ) -> BackupRecord | None:
        candidates = [
            item
            for item in self.records
            if (backup_type is None or item.backup_type is backup_type)
            and (not verified_only or item.status is BackupStatus.VERIFIED)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: utc_sort_key(item.created_at_utc))


class BackupHistory:
    """Read-only history scanner for one managed backup tree."""

    def __init__(self, directories: BackupDirectories) -> None:
        self._directories = directories

    @property
    def directories(self) -> BackupDirectories:
        return self._directories

    def scan(self) -> HistoryScan:
        records: list[BackupRecord] = []
        seen: set[str] = set()
        for backup_type, directory in (
            (BackupType.AUTOMATIC, self._directories.automatic),
            (BackupType.MANUAL, self._directories.manual),
            (BackupType.SAFETY, self._directories.safety),
        ):
            for record in self._scan_directory(directory, backup_type):
                key = str(record.path).lower()
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
        records.sort(
            key=lambda item: utc_sort_key(item.created_at_utc),
            reverse=True,
        )
        return HistoryScan(records=tuple(records))

    def latest(
        self,
        backup_type: BackupType | None = None,
        *,
        verified_only: bool = False,
    ) -> BackupRecord | None:
        return self.scan().latest(backup_type, verified_only=verified_only)

    def _scan_directory(self, directory: Path, backup_type: BackupType) -> list[BackupRecord]:
        if not directory.is_dir():
            return []

        records: dict[str, BackupRecord] = {}
        try:
            entries = list(directory.iterdir())
        except OSError:
            logger.warning("Backup history folder could not be read: %s", directory)
            return []

        database_files = {
            entry.name: entry
            for entry in entries
            if entry.is_file()
            and entry.name.lower().endswith(".db")
            and not entry.name.startswith(".")
        }
        metadata_files = {
            entry.name: entry
            for entry in entries
            if entry.is_file() and entry.name.lower().endswith(constants.BACKUP_METADATA_SUFFIX)
        }

        for name, path in sorted(database_files.items()):
            records[name.lower()] = self._record_for_file(path, backup_type)

        for name, path in sorted(metadata_files.items()):
            data_name = name[: -len(constants.BACKUP_METADATA_SUFFIX)]
            key = data_name.lower()
            if key in records:
                continue
            records[key] = self._record_for_orphan_metadata(path, data_name, backup_type)

        return list(records.values())

    def _record_for_file(self, path: Path, backup_type: BackupType) -> BackupRecord:
        meta_path = metadata_path_for(path)
        try:
            size = path.stat().st_size
        except OSError:
            size = None

        if not meta_path.is_file():
            return BackupRecord(
                path=path,
                backup_type=backup_type,
                status=BackupStatus.UNVERIFIED,
                file_name=path.name,
                metadata_path=None,
                size_bytes=size,
                detail="No metadata sidecar; the file cannot be trusted as a restore candidate.",
            )

        try:
            metadata = read_metadata(meta_path)
        except MetadataError as exc:
            return BackupRecord(
                path=path,
                backup_type=backup_type,
                status=BackupStatus.MALFORMED,
                file_name=path.name,
                metadata_path=meta_path,
                size_bytes=size,
                detail=str(exc),
            )

        if metadata.file_name.lower() != path.name.lower():
            return self._record_from_metadata(
                path,
                backup_type,
                metadata,
                BackupStatus.MALFORMED,
                "Metadata names a different backup file.",
            )
        if metadata.backup_type is not backup_type:
            return self._record_from_metadata(
                path,
                backup_type,
                metadata,
                BackupStatus.MALFORMED,
                "Metadata backup type does not match its folder.",
            )
        if not is_managed_backup_name(path.name):
            return self._record_from_metadata(
                path,
                backup_type,
                metadata,
                BackupStatus.UNVERIFIED,
                "The file name is not in the managed backup naming format.",
            )
        if size is not None and size != metadata.backup_bytes:
            return self._record_from_metadata(
                path,
                backup_type,
                metadata,
                BackupStatus.UNVERIFIED,
                "The file size no longer matches its metadata; verify again before restoring.",
            )
        if not metadata.verified:
            return self._record_from_metadata(
                path,
                backup_type,
                metadata,
                BackupStatus.MALFORMED,
                "Metadata does not record a successful verification.",
            )
        return self._record_from_metadata(
            path,
            backup_type,
            metadata,
            BackupStatus.VERIFIED,
            "Metadata is valid; restore still re-verifies the file.",
        )

    def _record_for_orphan_metadata(
        self,
        meta_path: Path,
        data_name: str,
        backup_type: BackupType,
    ) -> BackupRecord:
        path = meta_path.with_name(data_name)
        try:
            metadata = read_metadata(meta_path)
        except MetadataError as exc:
            return BackupRecord(
                path=path,
                backup_type=backup_type,
                status=BackupStatus.MALFORMED,
                file_name=data_name,
                metadata_path=meta_path,
                detail=str(exc),
            )
        return self._record_from_metadata(
            path,
            backup_type,
            metadata,
            BackupStatus.MISSING,
            "The metadata exists but the backup file is missing.",
        )

    @staticmethod
    def _record_from_metadata(
        path: Path,
        backup_type: BackupType,
        metadata: BackupMetadata,
        status: BackupStatus,
        detail: str,
    ) -> BackupRecord:
        return BackupRecord(
            path=path,
            backup_type=backup_type,
            status=status,
            file_name=path.name,
            metadata_path=metadata_path_for(path),
            created_at_utc=metadata.created_at_utc,
            size_bytes=metadata.backup_bytes if status is not BackupStatus.MISSING else None,
            schema_revision=metadata.schema_revision,
            verification_result=metadata.verification_result,
            detail=detail,
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = ["BackupHistory", "HistoryScan", "utc_now"]
