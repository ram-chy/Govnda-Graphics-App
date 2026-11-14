"""Validation of a user-selected business data location.

Validation is deliberately read-only towards the user's files. The only write is
a uniquely named probe file created, flushed, closed, and removed in the folder
that must prove write access. A protected system folder, a network path, the
application installation directory, or a drive that is not present is rejected
before any probe touches it.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from app.core import constants
from app.infrastructure.filesystem.drives import (
    DriveInfo,
    DriveType,
    drive_root,
    format_bytes,
    get_drive_info,
)
from app.infrastructure.filesystem.layout import DataRootLayout

logger = logging.getLogger(__name__)

_WINDOWS_MAX_PATH_WARNING = 240


class CheckStatus(StrEnum):
    """Severity of one validation row."""

    PASS = "pass"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    """One named result shown in the wizard's validation page."""

    key: str
    label: str
    status: CheckStatus
    message: str


@dataclass(frozen=True, slots=True)
class LocationValidationResult:
    """Complete outcome of validating one candidate data root."""

    root: Path | None
    checks: tuple[ValidationCheck, ...]
    drive: DriveInfo | None = None
    layout: DataRootLayout | None = None

    @property
    def errors(self) -> tuple[ValidationCheck, ...]:
        return tuple(check for check in self.checks if check.status is CheckStatus.ERROR)

    @property
    def warnings(self) -> tuple[ValidationCheck, ...]:
        return tuple(check for check in self.checks if check.status is CheckStatus.WARNING)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def error_summary(self) -> str:
        """Return the first error message, or a generic summary."""
        errors = self.errors
        if errors:
            return errors[0].message
        return "The selected location is not valid."


def default_installation_dirs() -> tuple[Path, ...]:
    """Return the directories that must never contain business data."""
    directories: list[Path] = []
    with contextlib.suppress(OSError):
        directories.append(Path(sys.executable).resolve().parent)
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        directories.append(Path(bundle_dir).resolve())
    repository = Path(__file__).resolve().parents[3]
    if (repository / "pyproject.toml").is_file():
        directories.append(repository)
    unique: list[Path] = []
    for directory in directories:
        if directory not in unique:
            unique.append(directory)
    return tuple(unique)


def default_protected_dirs() -> tuple[Path, ...]:
    """Return Windows system locations that are unsuitable for business data."""
    names = (
        "WINDIR",
        "SYSTEMROOT",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramW6432",
        "ProgramData",
    )
    directories: list[Path] = []
    for name in names:
        value = os.environ.get(name)
        if value:
            directory = Path(value)
            if directory.is_absolute() and directory not in directories:
                directories.append(directory)
    return tuple(directories)


class DataLocationValidator:
    """Check one candidate root without changing the user's files.

    The dependencies are injectable so validation policy can be tested without
    requiring a specific drive letter, a removable device, or a read-only disk.
    """

    def __init__(
        self,
        *,
        installation_dirs: Sequence[Path] | None = None,
        protected_dirs: Sequence[Path] | None = None,
        drive_info_provider: Callable[[Path], DriveInfo] = get_drive_info,
        write_probe: Callable[[Path], None] | None = None,
        minimum_free_bytes: int = constants.MINIMUM_FREE_SPACE_BYTES,
    ) -> None:
        self._installation_dirs = tuple(
            Path(item) for item in (installation_dirs or default_installation_dirs())
        )
        self._protected_dirs = tuple(
            Path(item)
            for item in (
                protected_dirs if protected_dirs is not None else default_protected_dirs()
            )
        )
        self._drive_info_provider = drive_info_provider
        self._write_probe = write_probe or _default_write_probe
        self._minimum_free_bytes = max(0, int(minimum_free_bytes))

    def validate(self, raw_path: str | Path | None) -> LocationValidationResult:
        """Return a complete, user-facing validation report."""
        checks: list[ValidationCheck] = []

        path = _normalise_path(raw_path)
        if path is None:
            checks.append(
                ValidationCheck(
                    "path",
                    "Path syntax",
                    CheckStatus.ERROR,
                    "Choose a folder path. The path cannot be empty or contain invalid characters.",
                )
            )
            return LocationValidationResult(root=None, checks=tuple(checks))

        checks.append(
            ValidationCheck("path", "Path syntax", CheckStatus.PASS, "The path is valid.")
        )

        if not path.is_absolute():
            checks.append(
                ValidationCheck(
                    "absolute",
                    "Absolute path",
                    CheckStatus.ERROR,
                    "Choose an absolute folder path such as D:\\GobindasBusiness.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks))
        checks.append(
            ValidationCheck(
                "absolute", "Absolute path", CheckStatus.PASS, "The path is absolute."
            )
        )

        if _is_unc(path):
            checks.append(
                ValidationCheck(
                    "network",
                    "Local folder",
                    CheckStatus.ERROR,
                    "Network and UNC paths are not supported for the live database. "
                    "Choose a folder on a local fixed or removable drive.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks))
        checks.append(
            ValidationCheck(
                "network",
                "Local folder",
                CheckStatus.PASS,
                "The path is local; no network share is used.",
            )
        )

        try:
            layout = DataRootLayout(path)
        except ValueError as exc:
            checks.append(
                ValidationCheck(
                    "layout",
                    "Folder path",
                    CheckStatus.ERROR,
                    f"The selected folder cannot be used: {exc}.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks))

        root = drive_root(path)
        if not root.anchor or not root.exists():
            checks.append(
                ValidationCheck(
                    "drive_available",
                    "Drive availability",
                    CheckStatus.ERROR,
                    f"The drive for {path} is not available. Reconnect the drive and try again.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks))
        checks.append(
            ValidationCheck(
                "drive_available",
                "Drive availability",
                CheckStatus.PASS,
                f"Drive {root} is available.",
            )
        )

        try:
            drive = self._drive_info_provider(root)
        except OSError:
            logger.debug("Drive information failed for %s", root, exc_info=True)
            drive = DriveInfo(root=root, drive_type=DriveType.UNKNOWN)

        if drive.drive_type is DriveType.UNAVAILABLE:
            checks.append(
                ValidationCheck(
                    "drive_type",
                    "Drive type",
                    CheckStatus.ERROR,
                    f"Drive {root} is not available.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks), drive=drive)
        if drive.drive_type is DriveType.NETWORK:
            checks.append(
                ValidationCheck(
                    "drive_type",
                    "Drive type",
                    CheckStatus.ERROR,
                    "Mapped network drives are not supported for the live database. "
                    "Choose a local or removable drive.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks), drive=drive)
        if drive.drive_type is DriveType.CDROM:
            checks.append(
                ValidationCheck(
                    "drive_type",
                    "Drive type",
                    CheckStatus.ERROR,
                    "An optical drive cannot store the live database. Choose another location.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks), drive=drive)

        if drive.is_removable:
            checks.append(
                ValidationCheck(
                    "drive_type",
                    "Drive type",
                    CheckStatus.WARNING,
                    f"{drive.describe()}. Keep this drive connected whenever the "
                    "application is used; removing it blocks startup.",
                )
            )
        elif drive.drive_type is DriveType.UNKNOWN:
            checks.append(
                ValidationCheck(
                    "drive_type",
                    "Drive type",
                    CheckStatus.WARNING,
                    "The drive type could not be identified. Continue only if this is a "
                    "local disk that remains connected.",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    "drive_type", "Drive type", CheckStatus.PASS, drive.describe()
                )
            )

        if _is_drive_root(path):
            checks.append(
                ValidationCheck(
                    "protected",
                    "Suitable folder",
                    CheckStatus.ERROR,
                    f"Choose a folder on drive {root}, not the drive root itself.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks), drive=drive)

        protected = _first_containing(path, self._protected_dirs)
        if protected is not None:
            checks.append(
                ValidationCheck(
                    "protected",
                    "Suitable folder",
                    CheckStatus.ERROR,
                    f"A Windows system or program folder cannot store business data ({protected}). "
                    "Choose a normal folder such as D:\\GobindasBusiness.",
                )
            )
            return LocationValidationResult(root=path, checks=tuple(checks), drive=drive)
        checks.append(
            ValidationCheck(
                "protected",
                "Suitable folder",
                CheckStatus.PASS,
                "The folder is not a protected Windows location.",
            )
        )

        installation = _first_containing(path, self._installation_dirs)
        if installation is not None:
            checks.append(
                ValidationCheck(
                    "installation",
                    "Separate from installation",
                    CheckStatus.ERROR,
                    "The business data folder cannot be inside the application installation "
                    f"directory ({installation}). Choose a separate folder.",
                )
            )
            return LocationValidationResult(
                root=path, checks=tuple(checks), drive=drive, layout=layout
            )
        checks.append(
            ValidationCheck(
                "installation",
                "Separate from installation",
                CheckStatus.PASS,
                "The folder is separate from the application installation.",
            )
        )

        if path.exists():
            if not path.is_dir():
                checks.append(
                    ValidationCheck(
                        "directory",
                        "Folder type",
                        CheckStatus.ERROR,
                        "The selected path is a file, not a folder. Choose a folder.",
                    )
                )
                return LocationValidationResult(
                    root=path, checks=tuple(checks), drive=drive, layout=layout
                )
            checks.append(
                ValidationCheck(
                    "directory",
                    "Folder type",
                    CheckStatus.PASS,
                    "The folder already exists.",
                )
            )
            if not _can_read_directory(path):
                checks.append(
                    ValidationCheck(
                        "read",
                        "Read access",
                        CheckStatus.ERROR,
                        "The folder cannot be read. Check its Windows permissions.",
                    )
                )
                return LocationValidationResult(
                    root=path, checks=tuple(checks), drive=drive, layout=layout
                )
            checks.append(
                ValidationCheck(
                    "read", "Read access", CheckStatus.PASS, "The folder is readable."
                )
            )
            probe_target = path
        else:
            ancestor = _nearest_existing_ancestor(path)
            if ancestor is None or not ancestor.is_dir():
                checks.append(
                    ValidationCheck(
                        "parent",
                        "Parent folder",
                        CheckStatus.ERROR,
                        "The parent folder does not exist or is a file. Choose a location "
                        "whose parent folder already exists.",
                    )
                )
                return LocationValidationResult(
                    root=path, checks=tuple(checks), drive=drive, layout=layout
                )
            if not _can_read_directory(ancestor):
                checks.append(
                    ValidationCheck(
                        "read",
                        "Read access",
                        CheckStatus.ERROR,
                        f"The parent folder ({ancestor}) cannot be read. Check its Windows "
                        "permissions.",
                    )
                )
                return LocationValidationResult(
                    root=path, checks=tuple(checks), drive=drive, layout=layout
                )
            checks.append(
                ValidationCheck(
                    "directory",
                    "Folder type",
                    CheckStatus.INFO,
                    "The folder does not exist yet and will be created during setup.",
                )
            )
            checks.append(
                ValidationCheck(
                    "read",
                    "Read access",
                    CheckStatus.PASS,
                    f"The parent folder ({ancestor.name or ancestor}) is readable.",
                )
            )
            probe_target = ancestor

        try:
            self._write_probe(probe_target)
        except OSError as exc:
            logger.info("Write probe failed in %s: %s", probe_target, exc)
            checks.append(
                ValidationCheck(
                    "write",
                    "Write access",
                    CheckStatus.ERROR,
                    f"The folder cannot be written to ({probe_target}). Check its Windows "
                    "permissions or choose another folder.",
                )
            )
            return LocationValidationResult(
                root=path, checks=tuple(checks), drive=drive, layout=layout
            )
        checks.append(
            ValidationCheck(
                "write", "Write access", CheckStatus.PASS, "A test file was written and removed."
            )
        )

        free_bytes = drive.free_bytes
        if free_bytes is None:
            try:
                free_bytes = int(shutil.disk_usage(probe_target).free)
            except OSError:
                logger.debug("Free space could not be read for %s", probe_target, exc_info=True)
        if free_bytes is None:
            checks.append(
                ValidationCheck(
                    "space",
                    "Available space",
                    CheckStatus.WARNING,
                    "Available free space could not be inspected.",
                )
            )
        elif free_bytes < self._minimum_free_bytes:
            checks.append(
                ValidationCheck(
                    "space",
                    "Available space",
                    CheckStatus.ERROR,
                    f"Only {format_bytes(free_bytes)} is free. At least "
                    f"{format_bytes(self._minimum_free_bytes)} is required to create the "
                    "database safely. Free space or choose another drive.",
                )
            )
            return LocationValidationResult(
                root=path, checks=tuple(checks), drive=drive, layout=layout
            )
        else:
            checks.append(
                ValidationCheck(
                    "space",
                    "Available space",
                    CheckStatus.PASS,
                    f"{format_bytes(free_bytes)} is available on drive {root}.",
                )
            )

        if len(str(path)) > _WINDOWS_MAX_PATH_WARNING:
            checks.append(
                ValidationCheck(
                    "path_length",
                    "Path length",
                    CheckStatus.WARNING,
                    "The path is long. A shorter folder path avoids Windows path-length "
                    "problems during backup and export.",
                )
            )

        database_path = layout.database_path
        if database_path.exists():
            if database_path.is_file():
                checks.append(
                    ValidationCheck(
                        "existing_database",
                        "Existing database",
                        CheckStatus.WARNING,
                        f"A database already exists at {database_path}. Setup will check it "
                        "and connect without overwriting it.",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        "existing_database",
                        "Existing database",
                        CheckStatus.ERROR,
                        f"The expected database path is a folder, not a file ({database_path}). "
                        "Choose another location.",
                    )
                )
                return LocationValidationResult(
                    root=path, checks=tuple(checks), drive=drive, layout=layout
                )
        else:
            checks.append(
                ValidationCheck(
                    "existing_database",
                    "Existing database",
                    CheckStatus.INFO,
                    "No database exists yet; setup will create one.",
                )
            )

        return LocationValidationResult(
            root=path,
            checks=tuple(checks),
            drive=drive,
            layout=layout,
        )


def _normalise_path(raw_path: str | Path | None) -> Path | None:
    if raw_path is None:
        return None
    if isinstance(raw_path, Path):
        return raw_path
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    text = raw_path.strip().strip('"')
    if "\x00" in text:
        return None
    try:
        return Path(text).expanduser()
    except (OSError, ValueError):
        return None


def _is_unc(path: Path) -> bool:
    text = str(path)
    return text.startswith("\\\\") or path.drive.startswith("\\\\")


def _is_drive_root(path: Path) -> bool:
    anchor = path.anchor
    if not anchor:
        return False
    try:
        return path == Path(anchor)
    except ValueError:  # pragma: no cover - defensive
        return False


def _first_containing(path: Path, candidates: Sequence[Path]) -> Path | None:
    for candidate in candidates:
        if _is_within(path, candidate):
            return candidate
    return None


def _is_within(child: Path, parent: Path) -> bool:
    try:
        return child.resolve(strict=False).is_relative_to(parent.resolve(strict=False))
    except (OSError, ValueError):
        return False


def _nearest_existing_ancestor(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        try:
            if candidate.exists():
                return candidate
        except OSError:  # pragma: no cover - defensive
            return None
    return None


def _can_read_directory(path: Path) -> bool:
    try:
        if not os.access(path, os.R_OK):
            return False
        with os.scandir(path) as entries:
            next(entries, None)
    except OSError:
        return False
    return True


def _default_write_probe(target: Path) -> None:
    """Create, flush, close, remove, and verify one uniquely named probe file."""
    descriptor, name = tempfile.mkstemp(
        prefix=".ggbms-setup-probe-", suffix=".tmp", dir=target
    )
    probe = Path(name)
    try:
        os.write(descriptor, b"GGBMS setup write probe\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    probe.unlink()
    if probe.exists():  # pragma: no cover - defensive against a hostile filesystem
        raise OSError(f"the write probe could not be removed: {probe}")


__all__ = [
    "CheckStatus",
    "DataLocationValidator",
    "LocationValidationResult",
    "ValidationCheck",
    "default_installation_dirs",
    "default_protected_dirs",
]
