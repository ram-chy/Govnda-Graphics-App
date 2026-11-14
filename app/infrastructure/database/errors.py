"""Classification and translation of SQLite/driver failures.

The database layer translates low-level errors into the application exception
hierarchy at its boundary. User-facing messages state what can be checked
(drive, folder, permissions, other copies) and never include SQL.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import DatabaseUnavailableError

DatabaseFailureKind = Literal["locked", "corrupt", "permission", "unavailable", "unknown"]

_LOCKED_MARKERS = (
    "database is locked",
    "database table is locked",
    "database schema is locked",
)
_CORRUPT_MARKERS = (
    "file is not a database",
    "database disk image is malformed",
    "malformed database schema",
    "file is encrypted or is not a database",
)
_PERMISSION_MARKERS = (
    "permission denied",
    "access is denied",
    "unable to open database file",
    "readonly database",
    "attempt to write a readonly database",
)
_UNAVAILABLE_MARKERS = (
    "no such file or directory",
    "the system cannot find the path specified",
    "the device is not ready",
    "the network path was not found",
)


def _error_texts(exc: BaseException) -> str:
    parts = [str(exc)]
    original = getattr(exc, "orig", None)
    if original is not None:
        parts.append(str(original))
    cause = exc.__cause__
    if cause is not None:
        parts.append(str(cause))
    return " ".join(parts).lower()


def classify_database_error(exc: BaseException) -> DatabaseFailureKind:
    """Map an exception to a stable failure kind for status reporting."""
    if isinstance(exc, PermissionError):
        return "permission"
    text = _error_texts(exc)
    if any(marker in text for marker in _CORRUPT_MARKERS):
        return "corrupt"
    if any(marker in text for marker in _LOCKED_MARKERS):
        return "locked"
    if any(marker in text for marker in _PERMISSION_MARKERS):
        return "permission"
    if any(marker in text for marker in _UNAVAILABLE_MARKERS):
        return "unavailable"
    return "unknown"


def user_message_for(kind: DatabaseFailureKind, path: Path | None = None) -> str:
    """Return a safe, actionable message for the failure kind."""
    location = f" ({path})" if path is not None else ""
    if kind == "locked":
        return (
            "The database is in use by another program. Close any other copies of the "
            "application and try again."
        )
    if kind == "corrupt":
        return (
            "The database file could not be opened because it may be damaged. The "
            "application will not delete or recreate it. Restore a verified backup or "
            "contact support."
        )
    if kind == "permission":
        return (
            f"The application does not have permission to access the database file"
            f"{location}. Check the folder permissions and that the drive is writable."
        )
    if kind == "unavailable":
        return (
            f"The configured database location is not available{location}. Check that "
            "the drive is connected and the data folder is correct."
        )
    return (
        f"The database could not be opened{location}. See the application log for "
        "technical details."
    )


def to_database_unavailable(
    exc: BaseException, path: Path | None = None
) -> DatabaseUnavailableError:
    """Wrap a driver failure as a :class:`DatabaseUnavailableError`."""
    kind = classify_database_error(exc)
    return DatabaseUnavailableError(
        f"database failure ({kind}) for {path!s}: {exc}",
        user_message=user_message_for(kind, path),
    )


def is_sqlite_error(exc: BaseException) -> bool:
    return isinstance(exc, (sqlite3.Error, SQLAlchemyError, OSError))
