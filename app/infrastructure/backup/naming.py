"""Unique, sortable backup file names.

A backup is never overwritten. Two backups created in the same second receive a
numeric suffix (``_2``, ``_3``, ...). The format follows the Phase 4 prompt:

``BusinessManagement_YYYY-MM-DD_HH-MM-SS_TYPE.db``

Sorted lexicographically, names within one type are also chronological.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from app.core import constants
from app.domain.backup import BackupType

_MANAGED_NAME = re.compile(
    rf"^{re.escape(constants.BACKUP_FILENAME_PREFIX)}_"
    r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_"
    r"(AUTOMATIC|MANUAL|SAFETY)(?:_\d+)?\.db$",
    re.IGNORECASE,
)


def is_managed_backup_name(name: str) -> bool:
    """Whether ``name`` is one of this application's published backup files.

    Retention uses this as a final guard so an unrelated ``.db`` file that a
    user copied into ``Backups\\Automatic`` is never deleted.
    """
    return bool(_MANAGED_NAME.match(name))


def backup_stem(backup_type: BackupType, created: datetime | None = None) -> str:
    """Return the timestamped stem for one backup type."""
    moment = created or datetime.now()
    stamp = moment.strftime(constants.BACKUP_TIMESTAMP_FORMAT)
    return f"{constants.BACKUP_FILENAME_PREFIX}_{stamp}_{backup_type.value.upper()}"


def backup_file_name(
    backup_type: BackupType,
    created: datetime | None = None,
    *,
    existing_names: Iterable[str] = (),
) -> str:
    """Return a name that does not collide with ``existing_names``.

    ``existing_names`` should include database and metadata files already in
    the destination folder. Case-insensitive comparison matches Windows
    filesystem behaviour.
    """
    taken = {name.lower() for name in existing_names}
    stem = backup_stem(backup_type, created)
    candidate = f"{stem}.db"
    counter = 2
    while candidate.lower() in taken:
        candidate = f"{stem}_{counter}.db"
        counter += 1
    return candidate


def backup_paths(
    directory: Path,
    backup_type: BackupType,
    created: datetime | None = None,
) -> tuple[Path, Path]:
    """Return the unique ``(database, metadata)`` paths inside ``directory``.

    The directory is not created here. Existing entries are inspected read-only.
    """
    folder = Path(directory)
    try:
        existing = [entry.name for entry in folder.iterdir()]
    except OSError:
        existing = []
    name = backup_file_name(backup_type, created, existing_names=existing)
    database_path = folder / name
    metadata_path = folder / f"{name}{constants.BACKUP_METADATA_SUFFIX}"
    return database_path, metadata_path


def metadata_path_for(database_path: Path) -> Path:
    """Return the sidecar path for a published backup file."""
    return Path(database_path).with_name(
        f"{Path(database_path).name}{constants.BACKUP_METADATA_SUFFIX}"
    )


def temp_path_for(database_path: Path) -> Path:
    """Return a unique temporary publish path next to the final backup.

    The name starts with a dot so it is not mistaken for a published backup and
    is easy to clean after an interrupted operation.
    """

    target = Path(database_path)
    token = uuid.uuid4().hex[:12]
    return target.with_name(f".{target.name}.{token}{constants.BACKUP_TEMP_SUFFIX}")


__all__ = [
    "backup_file_name",
    "backup_paths",
    "backup_stem",
    "is_managed_backup_name",
    "metadata_path_for",
    "temp_path_for",
]
