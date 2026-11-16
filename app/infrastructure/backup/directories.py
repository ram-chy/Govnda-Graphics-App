"""The three managed backup directories.

Only files inside these directories may ever be published, verified, or removed
by retention. The directories are derived from the approved data-root layout so
a backup can never be written next to an arbitrary user file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core import constants
from app.core.exceptions import BackupError
from app.domain.backup import BackupType
from app.infrastructure.filesystem.layout import DataRootLayout


@dataclass(frozen=True, slots=True)
class BackupDirectories:
    """Absolute paths of the managed backup storage tree."""

    root: Path
    automatic: Path
    manual: Path
    safety: Path

    def __post_init__(self) -> None:
        for name in ("root", "automatic", "manual", "safety"):
            value = Path(getattr(self, name))
            object.__setattr__(self, name, value)
            if not value.is_absolute():
                raise ValueError(f"{name} backup directory must be absolute")
        if self.root.name in ("", ".", ".."):
            raise ValueError("backup root must name a directory")

    @classmethod
    def from_layout(cls, layout: DataRootLayout) -> BackupDirectories:
        return cls(
            root=layout.backups_dir,
            automatic=layout.automatic_backups_dir,
            manual=layout.manual_backups_dir,
            safety=layout.safety_backups_dir,
        )

    def for_type(self, backup_type: BackupType) -> Path:
        return {
            BackupType.AUTOMATIC: self.automatic,
            BackupType.MANUAL: self.manual,
            BackupType.SAFETY: self.safety,
        }[backup_type]

    @property
    def managed(self) -> tuple[Path, ...]:
        return (self.automatic, self.manual, self.safety)

    @property
    def lock_path(self) -> Path:
        return self.root / constants.BACKUP_LOCK_FILENAME

    @property
    def state_path(self) -> Path:
        return self.root / constants.BACKUP_STATE_FILENAME

    @property
    def last_error_path(self) -> Path:
        return self.root / constants.BACKUP_LAST_ERROR_FILENAME

    def ensure(self) -> None:
        """Create the managed tree additively.

        A missing drive or an unwritable root raises :class:`BackupError`; the
        caller must never fall back to another location.
        """
        for directory in (self.root, *self.managed):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise BackupError(
                    f"backup directory could not be created: {directory}: {exc}",
                    user_message=(
                        f"The backup folder could not be created ({directory}). Check that "
                        "the drive is connected and the folder is writable."
                    ),
                ) from exc
            if not directory.is_dir():
                raise BackupError(
                    f"backup path is not a directory: {directory}",
                    user_message=f"The backup path is not a folder ({directory}).",
                )

    def contains(self, path: Path) -> bool:
        """Whether ``path`` is directly inside one of the managed directories."""
        candidate = Path(path)
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            return False
        for directory in self.managed:
            try:
                if resolved.parent == directory.resolve(strict=False):
                    return True
            except OSError:
                continue
        return False


__all__ = ["BackupDirectories"]
