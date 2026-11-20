"""Safe storage for managed business logo files."""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core import constants
from app.core.exceptions import AppError
from app.domain.business_logo import (
    ALLOWED_LOGO_EXTENSIONS,
    MAX_LOGO_BYTES,
    LogoValidation,
    validate_logo_content,
)
from app.infrastructure.backup.snapshot import fsync_directory
from app.infrastructure.filesystem.layout import DataRootLayout

Clock = Callable[[], str]


class LogoStorageError(AppError):
    """A logo could not be validated or stored safely."""


@dataclass(frozen=True, slots=True)
class StoredLogo:
    reference: str
    absolute_path: Path
    relative_path: str
    size_bytes: int
    sha256: str
    media_type: str


def _default_clock() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class LogoStorageService:
    """Write immutable, application-managed logo files under the data root."""

    def __init__(self, layout: DataRootLayout, *, clock: Clock | None = None) -> None:
        self._layout = layout
        self._clock = clock or _default_clock

    def store(self, source: Path, *, version_number: int) -> StoredLogo:
        source_path = Path(source)
        if not source_path.is_file():
            raise LogoStorageError(
                f"logo source is not a file: {source_path}",
                user_message="The selected logo file could not be read.",
            )

        extension = source_path.suffix.lower()
        try:
            size_bytes = source_path.stat().st_size
            with source_path.open("rb") as stream:
                header = stream.read(32)
                stream.seek(max(0, size_bytes - 32))
                tail = stream.read(32)
        except OSError as exc:
            raise LogoStorageError(
                f"logo source could not be read: {type(exc).__name__}",
                user_message="The selected logo file could not be read.",
            ) from exc

        validation = validate_logo_content(
            source_name=source_path.name,
            size_bytes=size_bytes,
            header=header,
            tail=tail,
        )
        _raise_validation(validation)

        target_dir = self._layout.logos_dir
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LogoStorageError(
                f"logo directory could not be created: {type(exc).__name__}",
                user_message="The managed logo folder could not be prepared.",
            ) from exc

        temp_path: Path | None = None
        final_path: Path | None = None
        try:
            descriptor, temp_name = tempfile.mkstemp(
                prefix=".logo-", suffix=constants.BACKUP_TEMP_SUFFIX, dir=target_dir
            )
            temp_path = Path(temp_name)
            digest = hashlib.sha256()
            written = 0
            with os.fdopen(descriptor, "wb") as output, source_path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
                output.flush()
                os.fsync(output.fileno())

            if written != size_bytes or written > MAX_LOGO_BYTES:
                raise LogoStorageError(
                    "logo changed while it was being stored",
                    user_message="The selected logo changed while it was being read. Try again.",
                )

            final_path = self._unique_target(version_number, extension)
            os.replace(temp_path, final_path)
            temp_path = None
            fsync_directory(target_dir)
            relative_path = f"{constants.DATA_LOGOS_DIR}/{final_path.name}"
            return StoredLogo(
                reference=relative_path,
                absolute_path=final_path,
                relative_path=relative_path,
                size_bytes=written,
                sha256=digest.hexdigest(),
                media_type=ALLOWED_LOGO_EXTENSIONS[extension],
            )
        except LogoStorageError:
            raise
        except OSError as exc:
            raise LogoStorageError(
                f"logo storage failed: {type(exc).__name__}",
                user_message="The logo could not be stored. The profile was not changed.",
            ) from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def resolve(self, reference: str) -> Path | None:
        if not reference:
            return None
        relative = Path(reference)
        if relative.is_absolute() or len(relative.parts) != 2:
            return None
        if relative.parts[0] != constants.DATA_LOGOS_DIR or ".." in relative.parts:
            return None
        candidate = (self._layout.root / relative).resolve()
        root = self._layout.root.resolve()
        if candidate.parent != (root / constants.DATA_LOGOS_DIR).resolve():
            return None
        return candidate if candidate.is_file() else None

    def discard(self, path: Path) -> None:
        candidate = Path(path)
        expected = self._layout.logos_dir.resolve()
        if candidate.parent.resolve() != expected:
            return
        candidate.unlink(missing_ok=True)

    def _unique_target(self, version_number: int, extension: str) -> Path:
        stamp = self._clock().replace(":", "-").replace("+", "_")
        while True:
            candidate = self._layout.logos_dir / (
                f"profile-{version_number}-{stamp}-{uuid.uuid4().hex}{extension}"
            )
            if not candidate.exists():
                return candidate


def _raise_validation(validation: LogoValidation) -> None:
    if validation.is_valid:
        return
    raise LogoStorageError(
        "logo validation failed",
        user_message=validation.errors.get("logo", "The selected logo is not valid."),
    )


__all__ = ["LogoStorageError", "LogoStorageService", "StoredLogo"]
