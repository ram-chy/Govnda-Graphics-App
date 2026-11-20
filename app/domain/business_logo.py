"""Logo rules that are independent of Qt, SQLAlchemy, and the filesystem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_LOGO_BYTES = 5 * 1024 * 1024
ALLOWED_LOGO_EXTENSIONS: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
JPEG_END_MARKER = b"\xff\xd9"


@dataclass(frozen=True, slots=True)
class LogoValidation:
    errors: dict[str, str]
    media_type: str = ""

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_logo_content(
    *,
    source_name: str,
    size_bytes: int,
    header: bytes,
    tail: bytes,
) -> LogoValidation:
    errors: dict[str, str] = {}
    extension = Path(source_name).suffix.lower()
    media_type = ALLOWED_LOGO_EXTENSIONS.get(extension, "")

    if not media_type:
        errors.setdefault("logo", "Choose a PNG, JPG, or JPEG image.")
    if size_bytes <= 0:
        errors.setdefault("logo", "The logo file is empty.")
    elif size_bytes > MAX_LOGO_BYTES:
        errors.setdefault("logo", "The logo must be 5 MB or smaller.")

    if extension == ".png":
        if not header.startswith(PNG_SIGNATURE) or header[12:16] != b"IHDR":
            errors.setdefault("logo", "The selected file is not a valid PNG image.")
    elif extension in (".jpg", ".jpeg") and (
        not header.startswith(JPEG_SIGNATURE) or JPEG_END_MARKER not in tail
    ):
        errors.setdefault("logo", "The selected file is not a valid JPEG image.")

    return LogoValidation(errors=errors, media_type=media_type)


__all__ = [
    "ALLOWED_LOGO_EXTENSIONS",
    "MAX_LOGO_BYTES",
    "LogoValidation",
    "validate_logo_content",
]
