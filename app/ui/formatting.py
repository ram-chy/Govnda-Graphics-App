"""Small formatting helpers shared by the Phase 4 views and dialogs."""

from __future__ import annotations

from datetime import datetime

from app.domain.backup import BackupStatus

_UNITS = ("bytes", "KB", "MB", "GB", "TB")


def format_backup_size(size: int | None) -> str:
    """Return a compact, non-financial file size. Sizes are exact byte counts."""
    if size is None:
        return "Unknown"
    value = float(max(0, size))
    unit = _UNITS[0]
    for candidate in _UNITS:
        unit = candidate
        if value < 1024 or candidate == _UNITS[-1]:
            break
        value /= 1024
    if unit == "bytes":
        return f"{int(value)} bytes"
    return f"{value:.1f} {unit}"


def format_backup_time(moment: datetime | None, *, fallback: str = "Never") -> str:
    if moment is None:
        return fallback
    try:
        return moment.astimezone().strftime("%d %b %Y, %H:%M")
    except (OSError, OverflowError, ValueError):
        return fallback


def format_status(status: BackupStatus | str) -> str:
    if isinstance(status, BackupStatus):
        return status.label
    return str(status)


__all__ = ["format_backup_size", "format_backup_time", "format_status"]
