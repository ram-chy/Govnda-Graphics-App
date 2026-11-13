"""Filesystem locations used by the application.

Configuration and logs deliberately live outside the future business data
folder (ADR-009). No database path is defined in Phase 1; the data folder is
chosen by the setup wizard in a later phase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.constants import APP_SLUG, CONFIG_FILENAME, LOG_FILENAME


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Concrete directories for machine-local application files."""

    config_dir: Path
    log_dir: Path

    def __post_init__(self) -> None:
        if not isinstance(self.config_dir, Path) or not isinstance(self.log_dir, Path):
            raise TypeError("config_dir and log_dir must be pathlib.Path instances")

    @property
    def config_file(self) -> Path:
        return self.config_dir / CONFIG_FILENAME

    def log_file(self, filename: str = LOG_FILENAME) -> Path:
        """Return a log file path inside the log directory.

        Only a bare filename is accepted so callers cannot escape the log
        directory through path separators.
        """
        if not filename or Path(filename).name != filename:
            raise ValueError("log filename must be a plain file name")
        return self.log_dir / filename

    def ensure_directories(self) -> None:
        """Create the configuration and log directories if they do not exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def default_paths() -> AppPaths:
    """Return the standard per-user paths on Windows.

    Uses ``%APPDATA%`` for configuration and ``%LOCALAPPDATA%`` for logs, with
    sensible fallbacks when the variables are unavailable (for example in a
    restricted test runner).
    """
    roaming = os.environ.get("APPDATA")
    local = os.environ.get("LOCALAPPDATA")
    home = Path.home()

    config_root = Path(roaming) if roaming else home / "AppData" / "Roaming"
    local_root = Path(local) if local else home / "AppData" / "Local"

    return AppPaths(
        config_dir=config_root / APP_SLUG,
        log_dir=local_root / APP_SLUG / "logs",
    )
