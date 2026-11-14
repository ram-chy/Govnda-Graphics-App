"""Drive classification helpers used by setup validation."""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.filesystem.drives import (
    DriveInfo,
    DriveType,
    drive_root,
    format_bytes,
    get_drive_info,
)


def test_drive_type_properties() -> None:
    assert DriveType.FIXED.is_local
    assert DriveType.REMOVABLE.is_local
    assert DriveType.RAMDISK.is_local
    assert not DriveType.NETWORK.is_local
    assert not DriveType.CDROM.is_local
    assert DriveType.REMOVABLE.requires_connection_warning
    assert not DriveType.FIXED.requires_connection_warning
    assert DriveType.UNAVAILABLE.display_name == "Drive not available"


def test_format_bytes_is_readable() -> None:
    assert format_bytes(None) == "unknown"
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024 * 5) == "5.0 MB"
    assert format_bytes(1024**4) == "1.0 TB"


def test_drive_root_returns_the_filesystem_anchor(tmp_path: Path) -> None:
    assert drive_root(tmp_path / "Business") == Path(tmp_path.anchor)


def test_get_drive_info_for_an_existing_path(tmp_path: Path) -> None:
    info = get_drive_info(tmp_path)

    assert info.root == Path(tmp_path.anchor)
    assert info.drive_type is not DriveType.UNAVAILABLE
    assert info.free_bytes is None or info.free_bytes >= 0
    assert info.total_bytes is None or info.total_bytes >= 0


def test_get_drive_info_for_a_missing_drive_is_unavailable() -> None:
    info = get_drive_info(Path("Q:\\GobindasBusiness"))

    assert info.drive_type is DriveType.UNAVAILABLE
    assert not info.is_available


def test_describe_includes_known_details() -> None:
    info = DriveInfo(
        root=Path("D:\\"),
        drive_type=DriveType.FIXED,
        label="Data",
        filesystem="NTFS",
        total_bytes=10,
        free_bytes=1024,
    )

    description = info.describe()

    assert "Local fixed drive" in description
    assert '"Data"' in description
    assert "NTFS" in description
    assert "1.0 KB free" in description
