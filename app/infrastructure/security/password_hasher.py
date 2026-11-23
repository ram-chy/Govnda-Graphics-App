"""Password hashing with owner-approved Argon2id and scrypt fallback.

Exact parameters come from ``AUTHENTICATION_SPECIFICATION.md`` §3.1.1:

* Argon2id via ``argon2-cffi``: time_cost=3, memory_cost=65536 KiB,
  parallelism=1, hash_len=32, 16-byte salt, PHC string.
* scrypt fallback: N=2**17, r=8, p=1, dklen=32, 16-byte salt, explicit
  ``maxmem`` above 128 MiB, self-describing encoded string.

No plaintext password, salt, or hash is ever logged or included in an
exception message. If neither approved algorithm can be initialized, hashing
fails closed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import secrets
from dataclasses import dataclass

from app.core.exceptions import PasswordHashingError

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 65536
ARGON2_PARALLELISM = 1
ARGON2_HASH_LENGTH = 32
SALT_LENGTH = 16

SCRYPT_N = 2**17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_MAXMEM = 140_000_000

_SCRYPT_PREFIX = "scrypt"


@dataclass(frozen=True, slots=True)
class HashFormat:
    """Parsed parameters of a stored self-describing hash string."""

    algorithm: str
    parameters: dict[str, int]
    salt: bytes
    digest: bytes


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _parse_parameters(fragment: str) -> dict[str, int]:
    parameters: dict[str, int] = {}
    for item in fragment.split(","):
        key, _, value = item.partition("=")
        if not key or not value:
            raise ValueError("malformed hash parameters")
        parameters[key] = int(value)
    return parameters


def parse_stored_hash(stored: str) -> HashFormat:
    """Parse a stored hash string without verifying it."""

    parts = stored.split("$")
    if len(parts) != 5:
        raise ValueError("unsupported hash format")
    algorithm, parameter_fragment, salt_text, digest_text, _trailer = parts
    if algorithm != _SCRYPT_PREFIX or _trailer:
        raise ValueError("unsupported hash algorithm")
    return HashFormat(
        algorithm=algorithm,
        parameters=_parse_parameters(parameter_fragment),
        salt=_decode(salt_text),
        digest=_decode(digest_text),
    )


class PasswordHasher:
    """Hash and verify passwords using the approved algorithms.

    ``prefer`` accepts ``"auto"`` (default), ``"argon2id"`` or ``"scrypt"``.
    Explicit selection is used by tests; production code should use ``auto``
    so Argon2id is preferred whenever the approved dependency is present.
    """

    def __init__(self, *, prefer: str = "auto") -> None:
        if prefer not in {"auto", "argon2id", "scrypt"}:
            raise PasswordHashingError("Unsupported hashing preference.")
        self._prefer = prefer
        self._argon2 = self._load_argon2() if prefer in {"auto", "argon2id"} else None
        if prefer == "argon2id" and self._argon2 is None:
            raise PasswordHashingError("Argon2id support is not available.")
        if self._argon2 is None and not self._scrypt_available():
            raise PasswordHashingError("No approved password hashing algorithm is available.")
        self.algorithm = "argon2id" if self._argon2 is not None else "scrypt"

    @staticmethod
    def _load_argon2() -> object | None:
        if importlib.util.find_spec("argon2") is None:
            return None
        try:
            from argon2 import PasswordHasher as Argon2PasswordHasher
            from argon2.low_level import Type

            return Argon2PasswordHasher(
                time_cost=ARGON2_TIME_COST,
                memory_cost=ARGON2_MEMORY_COST_KIB,
                parallelism=ARGON2_PARALLELISM,
                hash_len=ARGON2_HASH_LENGTH,
                salt_len=SALT_LENGTH,
                type=Type.ID,
            )
        except Exception as error:  # pragma: no cover - environment specific
            raise PasswordHashingError("Argon2id support could not be initialized.") from error

    @staticmethod
    def _scrypt_available() -> bool:
        return hasattr(hashlib, "scrypt")

    @property
    def parameters(self) -> str:
        if self.algorithm == "argon2id":
            return (
                f"argon2id t={ARGON2_TIME_COST} m={ARGON2_MEMORY_COST_KIB}KiB "
                f"p={ARGON2_PARALLELISM} hash_len={ARGON2_HASH_LENGTH} salt={SALT_LENGTH}"
            )
        return (
            f"scrypt N={SCRYPT_N} r={SCRYPT_R} p={SCRYPT_P} dklen={SCRYPT_DKLEN} "
            f"salt={SALT_LENGTH} maxmem={SCRYPT_MAXMEM}"
        )

    def hash(self, password: str) -> str:
        """Hash a password; the returned string is safe to persist."""

        if self._argon2 is not None:
            return str(self._argon2.hash(password))
        salt = secrets.token_bytes(SALT_LENGTH)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=SCRYPT_DKLEN,
            maxmem=SCRYPT_MAXMEM,
        )
        parameters = f"N={SCRYPT_N},r={SCRYPT_R},p={SCRYPT_P},dklen={SCRYPT_DKLEN}"
        return f"{_SCRYPT_PREFIX}${parameters}${_encode(salt)}${_encode(derived)}$"

    def verify(self, stored: str, password: str) -> bool:
        """Verify a password with constant-time comparison; never raise on a bad hash."""

        if not stored:
            return False
        if self._argon2 is not None and not stored.startswith(f"{_SCRYPT_PREFIX}$"):
            try:
                return bool(self._argon2.verify(stored, password))
            except Exception:
                return False
        try:
            parsed = parse_stored_hash(stored)
        except ValueError, TypeError:
            return False
        if parsed.algorithm != _SCRYPT_PREFIX or len(parsed.salt) != SALT_LENGTH:
            return False
        expected = parsed.parameters
        if expected.get("N") != SCRYPT_N or expected.get("r") != SCRYPT_R:
            return False
        if expected.get("p") != SCRYPT_P or expected.get("dklen") != SCRYPT_DKLEN:
            return False
        try:
            candidate = hashlib.scrypt(
                password.encode("utf-8"),
                salt=parsed.salt,
                n=SCRYPT_N,
                r=SCRYPT_R,
                p=SCRYPT_P,
                dklen=SCRYPT_DKLEN,
                maxmem=SCRYPT_MAXMEM,
            )
        except ValueError, MemoryError:
            return False
        return hmac.compare_digest(candidate, parsed.digest)

    def needs_rehash(self, stored: str) -> bool:
        """Return ``True`` when a stored hash uses superseded parameters."""

        if not stored:
            return True
        if self.algorithm == "argon2id":
            if stored.startswith(f"{_SCRYPT_PREFIX}$"):
                return True
            try:
                return bool(self._argon2.check_needs_rehash(stored))  # type: ignore[union-attr]
            except Exception:
                return True
        try:
            parsed = parse_stored_hash(stored)
        except ValueError, TypeError:
            return True
        return parsed.parameters != {
            "N": SCRYPT_N,
            "r": SCRYPT_R,
            "p": SCRYPT_P,
            "dklen": SCRYPT_DKLEN,
        }


__all__ = [
    "ARGON2_MEMORY_COST_KIB",
    "ARGON2_PARALLELISM",
    "ARGON2_TIME_COST",
    "SCRYPT_DKLEN",
    "SCRYPT_MAXMEM",
    "SCRYPT_N",
    "SCRYPT_P",
    "SCRYPT_R",
    "SALT_LENGTH",
    "HashFormat",
    "PasswordHasher",
    "parse_stored_hash",
]
