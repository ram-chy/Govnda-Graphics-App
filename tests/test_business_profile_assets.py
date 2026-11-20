"""Managed profile assets in backup, restore, and relocation."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.exceptions import RestoreError
from app.domain.backup import BackupType
from app.domain.backup_assets import ManagedBackupAsset
from app.infrastructure.backup.lock import OperationLock
from app.infrastructure.backup.metadata import (
    BackupMetadata,
    MetadataError,
    read_metadata,
)
from app.infrastructure.backup.naming import metadata_path_for
from app.infrastructure.backup.state import BackupStateStore
from app.infrastructure.database.migrations import application_head_revision
from app.infrastructure.filesystem.validation import DataLocationValidator
from app.services.backup_service import BackupService
from app.services.relocation_service import RelocationService
from app.services.restore_service import RestoreService
from tests.backup_helpers import (
    build_directories,
    build_runtime,
    create_data_root,
    fixed_clock,
    insert_probe,
    probe_values,
    save_location,
)

MOMENT = datetime(2026, 11, 20, 10, 30, tzinfo=UTC)
HEAD_REVISION = application_head_revision()
LOGO_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest"


def _backup_service(root: Path, database_path: Path) -> BackupService:
    directories = build_directories(root)
    return BackupService(
        directories=directories,
        database_path=database_path,
        lock=OperationLock(directories.lock_path, operation="backup"),
        state_store=BackupStateStore(directories.state_path),
        clock=fixed_clock(MOMENT),
        managed_asset_dirs=(root / "Logos",),
    )


def _restore_service(
    config_service, runtime, root: Path, backup_service: BackupService
) -> RestoreService:
    directories = build_directories(root)
    return RestoreService(
        config_service=config_service,
        runtime=runtime,
        directories=directories,
        lock=OperationLock(directories.lock_path, operation="restore"),
        backup_service=backup_service,
        expected_schema_revision=HEAD_REVISION,
        state_store=BackupStateStore(directories.state_path),
        clock=fixed_clock(MOMENT),
    )


def test_backup_embeds_managed_logo_files_in_verified_sidecar(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    logos = root / "Logos"
    logos.mkdir(parents=True, exist_ok=True)
    (logos / "logo.png").write_bytes(LOGO_BYTES)
    service = _backup_service(root, database_path)

    result = service.create_backup(BackupType.MANUAL, trigger="manual")
    loaded = read_metadata(metadata_path_for(result.path))

    assert len(result.metadata.managed_assets) == 1
    asset = result.metadata.managed_assets[0]
    assert asset.relative_path == "Logos/logo.png"
    assert asset.content == LOGO_BYTES
    assert loaded == result.metadata
    assert loaded.managed_assets[0].sha256 == asset.sha256


def test_metadata_without_managed_assets_remains_compatible(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    service = _backup_service(root, database_path)
    result = service.create_backup(BackupType.MANUAL, trigger="manual")
    data = result.metadata.to_dict()
    data.pop("managed_assets")

    loaded = BackupMetadata.from_dict(data)

    assert loaded.managed_assets == ()
    assert loaded.verified


def test_metadata_rejects_a_tampered_managed_asset(tmp_path: Path) -> None:
    root, database_path = create_data_root(tmp_path)
    logos = root / "Logos"
    logos.mkdir(parents=True, exist_ok=True)
    (logos / "logo.png").write_bytes(LOGO_BYTES)
    result = _backup_service(root, database_path).create_backup(
        BackupType.MANUAL, trigger="manual"
    )
    data = result.metadata.to_dict()
    data["managed_assets"][0]["content"] = base64.b64encode(
        b"x" * len(LOGO_BYTES)
    ).decode("ascii")

    with pytest.raises(MetadataError, match="checksum"):
        BackupMetadata.from_dict(data)


def test_backup_rejects_an_unsafe_managed_asset_path() -> None:
    with pytest.raises(ValueError, match="safe relative path"):
        ManagedBackupAsset(
            relative_path="Logos/../secret.png",
            size_bytes=1,
            sha256="a" * 64,
            content=b"x",
        )


def test_restore_replaces_the_managed_logo_directory(
    tmp_path: Path, config_service
) -> None:
    root, database_path = create_data_root(tmp_path)
    logos = root / "Logos"
    logos.mkdir(parents=True, exist_ok=True)
    (logos / "logo.png").write_bytes(LOGO_BYTES)
    backup_service = _backup_service(root, database_path)
    result = backup_service.create_backup(BackupType.MANUAL, trigger="manual")
    save_location(config_service, root, database_path)
    runtime = build_runtime(database_path)

    (logos / "logo.png").write_bytes(b"stale logo")
    restore_service = _restore_service(config_service, runtime, root, backup_service)
    candidate = restore_service.prepare(result.record)
    restored = restore_service.restore(candidate)

    assert restored.managed_assets_restored == 1
    assert (logos / "logo.png").read_bytes() == LOGO_BYTES
    assert runtime.database is not None
    runtime.close()


def test_failed_asset_replacement_rolls_back_database_and_logo(
    tmp_path: Path, config_service, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, database_path = create_data_root(tmp_path)
    logos = root / "Logos"
    logos.mkdir(parents=True, exist_ok=True)
    (logos / "logo.png").write_bytes(LOGO_BYTES)
    backup_service = _backup_service(root, database_path)
    result = backup_service.create_backup(BackupType.MANUAL, trigger="manual")
    insert_probe(database_path, "current-only")
    (logos / "logo.png").write_bytes(b"stale logo")
    save_location(config_service, root, database_path)
    runtime = build_runtime(database_path)
    restore_service = _restore_service(config_service, runtime, root, backup_service)

    def fail_asset_replacement(*_args: object) -> None:
        raise RestoreError("simulated managed asset failure")

    monkeypatch.setattr(
        restore_service, "_replace_managed_assets", fail_asset_replacement
    )

    with pytest.raises(RestoreError, match="rolled back"):
        restore_service.restore(restore_service.prepare(result.record))

    assert probe_values(database_path) == ["current-only"]
    assert (logos / "logo.png").read_bytes() == b"stale logo"
    assert runtime.database is not None
    runtime.close()


def test_relocation_copies_the_managed_logo_directory(
    tmp_path: Path, config_service
) -> None:
    old_root, database_path = create_data_root(tmp_path, name="Old")
    logos = old_root / "Logos"
    logos.mkdir(parents=True, exist_ok=True)
    (logos / "logo.png").write_bytes(LOGO_BYTES)
    backup_service = _backup_service(old_root, database_path)
    save_location(config_service, old_root, database_path)
    runtime = build_runtime(database_path)
    directories = build_directories(old_root)
    service = RelocationService(
        config_service=config_service,
        runtime=runtime,
        lock=OperationLock(directories.lock_path, operation="relocation"),
        backup_service=backup_service,
        validator=DataLocationValidator(),
        state_store=BackupStateStore(directories.state_path),
        clock=fixed_clock(MOMENT),
    )
    new_root = tmp_path / "New"

    result = service.relocate(new_root)

    assert result.managed_assets_relocated == 1
    assert (new_root / "Logos" / "logo.png").read_bytes() == LOGO_BYTES
    assert (old_root / "Logos" / "logo.png").read_bytes() == LOGO_BYTES
    assert config_service.load().data_root == str(new_root)
    runtime.close()
