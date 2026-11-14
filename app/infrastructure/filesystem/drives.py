"""Drive classification and free-space inspection for the setup wizard.

Windows exposes the drive type and volume information through kernel32. The
module degrades to a conservative fixed-drive assumption on other platforms so
tests and development remain possible; the shipped application targets Windows.
"""

from __future__ import annotations

import ctypes
import logging
import shutil
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

_DRIVE_TYPE_UNKNOWN = 0
_DRIVE_TYPE_NO_ROOT = 1
_DRIVE_TYPE_REMOVABLE = 2
_DRIVE_TYPE_FIXED = 3
_DRIVE_TYPE_REMOTE = 4
_DRIVE_TYPE_CDROM = 5
_DRIVE_TYPE_RAMDISK = 6


class DriveType(StrEnum):
    """Stable drive categories used by validation and the summary UI."""

    FIXED = "fixed"
    REMOVABLE = "removable"
    NETWORK = "network"
    CDROM = "cdrom"
    RAMDISK = "ramdisk"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"

    @property
    def is_local(self) -> bool:
        """Whether the drive is suitable for a live SQLite database."""
        return self in (DriveType.FIXED, DriveType.REMOVABLE, DriveType.RAMDISK)

    @property
    def requires_connection_warning(self) -> bool:
        return self is DriveType.REMOVABLE

    @property
    def display_name(self) -> str:
        return {
            DriveType.FIXED: "Local fixed drive",
            DriveType.REMOVABLE: "Removable drive",
            DriveType.NETWORK: "Network drive",
            DriveType.CDROM: "Optical drive",
            DriveType.RAMDISK: "RAM disk",
            DriveType.UNKNOWN: "Unknown drive type",
            DriveType.UNAVAILABLE: "Drive not available",
        }[self]


_DRIVE_TYPE_NAMES: dict[int, DriveType] = {
    _DRIVE_TYPE_UNKNOWN: DriveType.UNKNOWN,
    _DRIVE_TYPE_NO_ROOT: DriveType.UNAVAILABLE,
    _DRIVE_TYPE_REMOVABLE: DriveType.REMOVABLE,
    _DRIVE_TYPE_FIXED: DriveType.FIXED,
    _DRIVE_TYPE_REMOTE: DriveType.NETWORK,
    _DRIVE_TYPE_CDROM: DriveType.CDROM,
    _DRIVE_TYPE_RAMDISK: DriveType.RAMDISK,
}


@dataclass(frozen=True, slots=True)
class DriveInfo:
    """What can be discovered about the drive that contains a path."""

    root: Path
    drive_type: DriveType
    label: str | None = None
    filesystem: str | None = None
    total_bytes: int | None = None
    free_bytes: int | None = None

    @property
    def is_available(self) -> bool:
        return self.drive_type is not DriveType.UNAVAILABLE

    @property
    def is_removable(self) -> bool:
        return self.drive_type is DriveType.REMOVABLE

    def describe(self) -> str:
        parts = [self.drive_type.display_name]
        if self.label:
            parts.append(f'"{self.label}"')
        if self.filesystem:
            parts.append(self.filesystem)
        if self.free_bytes is not None:
            parts.append(f"{format_bytes(self.free_bytes)} free")
        return " · ".join(parts)


def drive_root(path: Path) -> Path:
    """Return the Windows drive root (``D:\\``) or the filesystem anchor."""
    anchor = Path(path).anchor
    return Path(anchor) if anchor else Path(path)


def format_bytes(value: int | None) -> str:
    """Format a byte count for a calm, readable UI summary."""
    if value is None:
        return "unknown"
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} B"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def get_drive_info(path: Path) -> DriveInfo:
    """Inspect the drive containing ``path`` without requiring the path to exist."""
    root = drive_root(path)
    if not root.anchor or not root.exists():
        return DriveInfo(root=root, drive_type=DriveType.UNAVAILABLE)

    drive_type = _windows_drive_type(root) if sys.platform == "win32" else DriveType.FIXED
    label: str | None = None
    filesystem: str | None = None
    if sys.platform == "win32":
        label, filesystem = _windows_volume_info(root)

    total_bytes: int | None = None
    free_bytes: int | None = None
    try:
        usage = shutil.disk_usage(root)
    except OSError:
        logger.debug("Free space could not be inspected for %s", root, exc_info=True)
    else:
        total_bytes = int(usage.total)
        free_bytes = int(usage.free)

    return DriveInfo(
        root=root,
        drive_type=drive_type,
        label=label,
        filesystem=filesystem,
        total_bytes=total_bytes,
        free_bytes=free_bytes,
    )


def _windows_drive_type(root: Path) -> DriveType:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
        kernel32.GetDriveTypeW.restype = ctypes.c_uint
        code = int(kernel32.GetDriveTypeW(str(root)))
    except (AttributeError, OSError, ValueError):
        logger.debug("Drive type could not be read for %s", root, exc_info=True)
        return DriveType.UNKNOWN
    return _DRIVE_TYPE_NAMES.get(code, DriveType.UNKNOWN)


def _windows_volume_info(root: Path) -> tuple[str | None, str | None]:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetVolumeInformationW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.c_wchar_p,
            ctypes.c_uint,
        ]
        kernel32.GetVolumeInformationW.restype = ctypes.c_int
        volume_name = ctypes.create_unicode_buffer(261)
        filesystem_name = ctypes.create_unicode_buffer(261)
        serial = ctypes.c_uint(0)
        maximum_component = ctypes.c_uint(0)
        flags = ctypes.c_uint(0)
        ok = kernel32.GetVolumeInformationW(
            str(root),
            volume_name,
            261,
            ctypes.byref(serial),
            ctypes.byref(maximum_component),
            ctypes.byref(flags),
            filesystem_name,
            261,
        )
    except (AttributeError, OSError, ValueError):
        logger.debug("Volume information could not be read for %s", root, exc_info=True)
        return None, None
    if not ok:
        return None, None
    return volume_name.value or None, filesystem_name.value or None


__all__ = [
    "DriveInfo",
    "DriveType",
    "drive_root",
    "format_bytes",
    "get_drive_info",
]
