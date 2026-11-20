"""Managed file assets embedded in a backup sidecar."""

from __future__ import annotations

import base64
import binascii
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath


class ManagedAssetError(ValueError):
    """A managed asset manifest entry is unsafe or inconsistent."""


@dataclass(frozen=True, slots=True)
class ManagedBackupAsset:
    relative_path: str
    size_bytes: int
    sha256: str
    content: bytes

    def __post_init__(self) -> None:
        path = validate_relative_path(self.relative_path)
        object.__setattr__(self, "relative_path", path)
        if self.size_bytes != len(self.content):
            raise ManagedAssetError("managed asset size does not match its content")
        digest = hashlib.sha256(self.content).hexdigest()
        if self.sha256 != digest:
            raise ManagedAssetError("managed asset checksum does not match its content")

    def to_dict(self) -> dict[str, str | int]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "content": base64.b64encode(self.content).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ManagedBackupAsset:
        if not isinstance(data, Mapping):
            raise ManagedAssetError("managed asset entry must be an object")
        relative_path = data.get("relative_path")
        size = data.get("size_bytes")
        digest = data.get("sha256")
        content = data.get("content")
        if not isinstance(relative_path, str) or not isinstance(content, str):
            raise ManagedAssetError("managed asset entry has invalid text fields")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ManagedAssetError("managed asset size must be a non-negative integer")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ManagedAssetError("managed asset checksum must be a SHA-256 digest")
        try:
            raw = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ManagedAssetError("managed asset content is not valid base64") from exc
        return cls(
            relative_path=relative_path,
            size_bytes=size,
            sha256=digest.lower(),
            content=raw,
        )


def validate_relative_path(value: str) -> str:
    if not value or "\\" in value or value.startswith("/"):
        raise ManagedAssetError("managed asset path is not a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ManagedAssetError("managed asset path is not a safe relative path")
    if len(path.parts) < 2:
        raise ManagedAssetError("managed asset path must include a managed folder")
    return path.as_posix()


__all__ = ["ManagedAssetError", "ManagedBackupAsset", "validate_relative_path"]
