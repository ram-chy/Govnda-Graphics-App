"""Approved business data root layout.

The user selects one root folder. Everything the application later needs lives
below it in fixed, documented locations (BACKUP_STRATEGY.md §2). The database
file name is fixed so recovery can find it without guessing, but the absolute
path is always supplied explicitly rather than derived from the working
directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core import constants


@dataclass(frozen=True, slots=True)
class DataRootLayout:
    """Paths derived from one selected business data root."""

    root: Path
    database_file_name: str = constants.DATABASE_FILENAME

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))
        if not self.root.is_absolute():
            raise ValueError("data root must be an absolute path")
        if self.root.name in ("", ".", ".."):
            raise ValueError("data root must name a directory")
        if (
            not self.database_file_name
            or Path(self.database_file_name).name != self.database_file_name
        ):
            raise ValueError("database file name must be a plain file name")

    @property
    def database_dir(self) -> Path:
        return self.root / constants.DATA_DATABASE_DIR

    @property
    def database_path(self) -> Path:
        return self.database_dir / self.database_file_name

    @property
    def backups_dir(self) -> Path:
        return self.root / constants.DATA_BACKUPS_DIR

    @property
    def automatic_backups_dir(self) -> Path:
        return self.backups_dir / constants.DATA_BACKUPS_AUTOMATIC_DIR

    @property
    def manual_backups_dir(self) -> Path:
        return self.backups_dir / constants.DATA_BACKUPS_MANUAL_DIR

    @property
    def safety_backups_dir(self) -> Path:
        return self.backups_dir / constants.DATA_BACKUPS_SAFETY_DIR

    @property
    def attachments_dir(self) -> Path:
        return self.root / constants.DATA_ATTACHMENTS_DIR

    @property
    def exports_dir(self) -> Path:
        return self.root / constants.DATA_EXPORTS_DIR

    @property
    def pdf_exports_dir(self) -> Path:
        return self.exports_dir / constants.DATA_EXPORTS_PDF_DIR

    @property
    def excel_exports_dir(self) -> Path:
        return self.exports_dir / constants.DATA_EXPORTS_EXCEL_DIR

    def required_directories(self) -> tuple[Path, ...]:
        """Return every directory the setup wizard must create, in order."""
        return (
            self.root,
            self.database_dir,
            self.backups_dir,
            self.automatic_backups_dir,
            self.manual_backups_dir,
            self.safety_backups_dir,
            self.attachments_dir,
            self.exports_dir,
            self.pdf_exports_dir,
            self.excel_exports_dir,
        )

    def directory_purposes(self) -> tuple[tuple[Path, str], ...]:
        """Return each directory with a short human-readable purpose."""
        return (
            (self.root, "Business data root"),
            (self.database_dir, "Live SQLite database"),
            (self.backups_dir, "Backup storage"),
            (self.automatic_backups_dir, "Scheduled backups (Phase 4)"),
            (self.manual_backups_dir, "Manual backups (Phase 4)"),
            (self.safety_backups_dir, "Pre-upgrade and pre-restore safety copies (Phase 4)"),
            (self.attachments_dir, "Scanned documents and images"),
            (self.exports_dir, "Generated PDF and Excel exports"),
            (self.pdf_exports_dir, "PDF exports"),
            (self.excel_exports_dir, "Excel exports"),
        )


__all__ = ["DataRootLayout"]
