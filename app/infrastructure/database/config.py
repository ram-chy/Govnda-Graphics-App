"""Injected database location and connection configuration.

Nothing in the database layer derives a path from the project directory or from
the current working directory. The path is supplied by application
configuration (``AppConfig.database_path``) or constructed explicitly by a tool
or test. A missing parent directory is an error; it is never created silently.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL

from app.core.exceptions import DatabaseUnavailableError
from app.infrastructure.database.errors import to_database_unavailable

DEFAULT_BUSY_TIMEOUT_MS = 5_000
_MAX_BUSY_TIMEOUT_MS = 600_000


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Location and connection settings for one SQLite database.

    Args:
        path: Absolute path to the database file. The file may not exist yet
            when creating a new database.
        busy_timeout_ms: How long SQLite waits for a lock before returning
            ``database is locked``. Five seconds is the architecture default.
    """

    path: Path
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        if not self.path.is_absolute():
            raise ValueError("database path must be absolute")
        if self.path.name in ("", ".", ".."):
            raise ValueError("database path must name a database file")
        if (
            isinstance(self.busy_timeout_ms, bool)
            or not isinstance(self.busy_timeout_ms, int)
            or not 1 <= self.busy_timeout_ms <= _MAX_BUSY_TIMEOUT_MS
        ):
            raise ValueError(
                f"busy_timeout_ms must be an integer from 1 to {_MAX_BUSY_TIMEOUT_MS}"
            )

    @property
    def parent(self) -> Path:
        return self.path.parent

    @property
    def busy_timeout_seconds(self) -> float:
        return self.busy_timeout_ms / 1000

    @property
    def url(self) -> URL:
        """SQLAlchemy URL for this file, independent of the working directory."""
        return URL.create("sqlite", database=str(self.path))

    @property
    def wal_path(self) -> Path:
        return self.path.with_name(f"{self.path.name}-wal")

    @property
    def shm_path(self) -> Path:
        return self.path.with_name(f"{self.path.name}-shm")

    def validate_parent(self) -> None:
        """Verify that the parent folder exists, without creating it."""
        anchor = self.path.anchor
        if anchor and not Path(anchor).exists():
            raise DatabaseUnavailableError(
                f"database drive is unavailable: {anchor}",
                user_message=(
                    f"The drive for the configured database is not available ({anchor}). "
                    "Reconnect the drive and try again. The application will not create a "
                    "database elsewhere."
                ),
            )
        parent = self.parent
        if not parent.exists():
            raise DatabaseUnavailableError(
                f"database parent directory does not exist: {parent}",
                user_message=(
                    f"The folder that should contain the database does not exist ({parent}). "
                    "Choose the correct data folder; the application will not create a "
                    "database elsewhere."
                ),
            )
        if not parent.is_dir():
            raise DatabaseUnavailableError(
                f"database parent path is not a directory: {parent}",
                user_message=f"The configured database folder is not a directory ({parent}).",
            )

    def verify_writable_parent(self) -> None:
        """Prove that a file can be created in the parent folder.

        The probe file is created with an exclusive temporary name and removed
        immediately. It never touches the database file itself.
        """
        self.validate_parent()
        probe_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=".ggbms-write-", suffix=".tmp", dir=self.parent
            )
            os.close(descriptor)
            probe_path = Path(name)
        except OSError as exc:
            raise to_database_unavailable(exc, self.parent) from exc
        finally:
            if probe_path is not None:
                probe_path.unlink(missing_ok=True)

    def require_existing_file(self) -> None:
        """Raise when the configured database file is absent.

        Existing files are never created or replaced by this method.
        """
        self.validate_parent()
        if not self.path.exists():
            raise DatabaseUnavailableError(
                f"database file does not exist: {self.path}",
                user_message=(
                    f"The configured database file does not exist ({self.path}). Check that "
                    "the drive is connected and the data folder is correct. The application "
                    "will not create a database automatically."
                ),
            )
        if not self.path.is_file():
            raise DatabaseUnavailableError(
                f"database path is not a file: {self.path}",
                user_message=f"The configured database path is not a file ({self.path}).",
            )

    def require_absent_file(self) -> None:
        """Raise when a database file already exists at the configured path."""
        self.validate_parent()
        if self.path.exists():
            raise DatabaseUnavailableError(
                f"database file already exists: {self.path}",
                user_message=(
                    f"A database file already exists at {self.path}. Choose a new location or "
                    "open the existing database instead."
                ),
            )
