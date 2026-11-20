"""Validated JSON sidecar metadata for every published backup.

The sidecar is advisory history: a backup file without valid metadata is shown
as unverified and is never offered as a restore candidate. Metadata is written
atomically after the database file has been verified and published.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core import constants
from app.core.exceptions import BackupError
from app.domain.backup import BackupType
from app.domain.backup_assets import ManagedAssetError, ManagedBackupAsset
from app.infrastructure.backup.hashing import is_sha256

_REQUIRED_TEXT = (
    "file_name",
    "app_version",
    "schema_revision",
    "source_database_path",
    "verification_result",
    "integrity_check",
    "foreign_key_check",
    "operation_result",
    "trigger",
)


class MetadataError(BackupError):
    """A metadata sidecar is missing, malformed, or inconsistent."""


@dataclass(frozen=True, slots=True)
class BackupMetadata:
    """The durable description of one verified backup file."""

    file_name: str
    backup_type: BackupType
    created_at_utc: datetime
    app_version: str
    application_id: int
    schema_revision: str
    source_database_path: str
    source_database_bytes: int
    backup_bytes: int
    sha256: str
    verification_result: str
    integrity_check: str
    foreign_key_check: str
    operation_result: str
    duration_ms: int
    trigger: str
    created_at_local: str | None = None
    meta_version: int = constants.BACKUP_METADATA_VERSION
    managed_assets: tuple[ManagedBackupAsset, ...] = ()

    def __post_init__(self) -> None:
        if self.created_at_utc.tzinfo is None:
            object.__setattr__(
                self, "created_at_utc", self.created_at_utc.replace(tzinfo=UTC)
            )

    @property
    def verified(self) -> bool:
        return (
            self.verification_result == "verified"
            and self.operation_result == "success"
            and self.integrity_check == "ok"
            and self.foreign_key_check == "ok"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_version": self.meta_version,
            "file_name": self.file_name,
            "backup_type": self.backup_type.value,
            "created_at_utc": _format_utc(self.created_at_utc),
            "created_at_local": self.created_at_local,
            "app_version": self.app_version,
            "application_id": self.application_id,
            "schema_revision": self.schema_revision,
            "source_database_path": self.source_database_path,
            "source_database_bytes": self.source_database_bytes,
            "backup_bytes": self.backup_bytes,
            "sha256": self.sha256,
            "verification_result": self.verification_result,
            "integrity_check": self.integrity_check,
            "foreign_key_check": self.foreign_key_check,
            "operation_result": self.operation_result,
            "duration_ms": self.duration_ms,
            "trigger": self.trigger,
            "managed_assets": [asset.to_dict() for asset in self.managed_assets],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BackupMetadata:
        if not isinstance(data, Mapping):
            raise MetadataError("backup metadata root must be a JSON object")
        for key in _REQUIRED_TEXT:
            value = data.get(key)
            if not isinstance(value, str) or not value:
                raise MetadataError(f"backup metadata field {key!r} must be a non-empty text")

        meta_version = _integer(data, "meta_version")
        if meta_version != constants.BACKUP_METADATA_VERSION:
            raise MetadataError(
                f"unsupported backup metadata version {meta_version!r}"
            )
        try:
            backup_type = BackupType(str(data["backup_type"]))
        except ValueError as exc:
            raise MetadataError("backup metadata has an unknown backup type") from exc

        file_name = str(data["file_name"])
        if Path(file_name).name != file_name or not file_name.lower().endswith(".db"):
            raise MetadataError("backup metadata file_name is not a plain .db file name")

        created = _parse_utc(str(data["created_at_utc"]))
        application_id = _integer(data, "application_id")
        source_bytes = _integer(data, "source_database_bytes")
        backup_bytes = _integer(data, "backup_bytes")
        duration_ms = _integer(data, "duration_ms")
        if source_bytes < 0 or backup_bytes <= 0 or duration_ms < 0:
            raise MetadataError("backup metadata contains an impossible size or duration")

        digest = str(data["sha256"])
        if not is_sha256(digest):
            raise MetadataError("backup metadata sha256 is not a lowercase SHA-256 digest")

        local = data.get("created_at_local")
        if local is not None and not isinstance(local, str):
            raise MetadataError("backup metadata created_at_local must be text")

        return cls(
            file_name=file_name,
            backup_type=backup_type,
            created_at_utc=created,
            app_version=str(data["app_version"]),
            application_id=application_id,
            schema_revision=str(data["schema_revision"]),
            source_database_path=str(data["source_database_path"]),
            source_database_bytes=source_bytes,
            backup_bytes=backup_bytes,
            sha256=digest,
            verification_result=str(data["verification_result"]),
            integrity_check=str(data["integrity_check"]),
            foreign_key_check=str(data["foreign_key_check"]),
            operation_result=str(data["operation_result"]),
            duration_ms=duration_ms,
            trigger=str(data["trigger"]),
            created_at_local=local,
            meta_version=meta_version,
            managed_assets=_managed_assets(data),
        )


def read_metadata(path: Path) -> BackupMetadata:
    """Read and validate one sidecar, raising :class:`MetadataError`."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise MetadataError(f"backup metadata could not be read: {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MetadataError(f"backup metadata is not valid JSON: {path}: {exc}") from exc
    return BackupMetadata.from_dict(data)


def write_metadata_atomic(path: Path, metadata: BackupMetadata) -> None:
    """Write a sidecar with a same-directory temporary file and atomic replace."""
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise MetadataError(
            f"backup metadata folder could not be created: {target.parent}"
        ) from exc

    temp_path: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=".backup-meta-", suffix=constants.BACKUP_TEMP_SUFFIX, dir=target.parent
        )
        temp_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(metadata.to_dict(), stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
        temp_path = None
    except OSError as exc:
        raise MetadataError(f"backup metadata could not be written: {target}: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _managed_assets(data: Mapping[str, Any]) -> tuple[ManagedBackupAsset, ...]:
    raw = data.get("managed_assets", [])
    if not isinstance(raw, list):
        raise MetadataError("backup metadata managed_assets must be a list")
    assets: list[ManagedBackupAsset] = []
    seen: set[str] = set()
    for entry in raw:
        try:
            asset = ManagedBackupAsset.from_dict(entry)
        except ManagedAssetError as exc:
            raise MetadataError(f"backup metadata managed asset is invalid: {exc}") from exc
        if not asset.relative_path.startswith(f"{constants.DATA_LOGOS_DIR}/"):
            raise MetadataError("backup metadata managed asset is outside a managed folder")
        if asset.relative_path in seen:
            raise MetadataError("backup metadata contains duplicate managed asset paths")
        seen.add(asset.relative_path)
        assets.append(asset)
    return tuple(assets)


def _integer(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise MetadataError(f"backup metadata field {key!r} must be an integer")
    return value


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MetadataError("backup metadata created_at_utc is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = [
    "BackupMetadata",
    "MetadataError",
    "read_metadata",
    "write_metadata_atomic",
]
