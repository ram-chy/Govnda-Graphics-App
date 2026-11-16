"""File hashing helpers used by backup and restore verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_BYTES = 1024 * 1024
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 hex digest of ``path``.

    The file is read in bounded chunks so a large database does not need to fit
    in memory. A missing or unreadable file raises :class:`OSError`.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            chunk = stream.read(_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sha256_matches(path: Path, expected: str) -> bool:
    """Compare a file hash in constant time against ``expected``."""
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest() == expected


def is_sha256(value: object) -> bool:
    """Whether ``value`` looks like a lowercase SHA-256 hex digest."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def empty_file_sha256() -> str:
    """Return the digest of an empty file (diagnostics and tests)."""
    return _EMPTY_SHA256


__all__ = ["empty_file_sha256", "is_sha256", "sha256_file", "sha256_matches"]
