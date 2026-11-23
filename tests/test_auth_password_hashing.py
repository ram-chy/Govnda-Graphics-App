"""Password hashing tests for the approved Argon2id and scrypt design."""

from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest

from app.core.exceptions import PasswordHashingError
from app.infrastructure.security.password_hasher import (
    ARGON2_MEMORY_COST_KIB,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
    SALT_LENGTH,
    SCRYPT_DKLEN,
    SCRYPT_MAXMEM,
    SCRYPT_N,
    SCRYPT_P,
    SCRYPT_R,
    PasswordHasher,
    parse_stored_hash,
)

PASSWORD = "CorrectHorse9"
WRONG_PASSWORD = "WrongHorse9"


def test_argon2id_is_preferred_with_approved_parameters() -> None:
    hasher = PasswordHasher(prefer="auto")

    assert hasher.algorithm == "argon2id"
    stored = hasher.hash(PASSWORD)
    assert stored.startswith("$argon2id$")
    assert f"m={ARGON2_MEMORY_COST_KIB}" in stored
    assert f"t={ARGON2_TIME_COST}" in stored
    assert f"p={ARGON2_PARALLELISM}" in stored
    assert not hasher.needs_rehash(stored)


def test_hash_verification_never_leaks_or_accepts_malformed_input() -> None:
    hasher = PasswordHasher()
    stored = hasher.hash(PASSWORD)

    assert hasher.verify(stored, PASSWORD)
    assert not hasher.verify(stored, WRONG_PASSWORD)
    assert not hasher.verify("not-a-hash", PASSWORD)
    assert not hasher.verify("", PASSWORD)


def test_plaintext_password_is_not_persisted() -> None:
    stored = PasswordHasher().hash(PASSWORD)

    assert PASSWORD not in stored
    assert WRONG_PASSWORD not in stored


def test_scrypt_fallback_uses_exact_approved_parameters() -> None:
    hasher = PasswordHasher(prefer="scrypt")
    assert hasher.algorithm == "scrypt"

    stored = hasher.hash(PASSWORD)
    parsed = parse_stored_hash(stored)
    assert parsed.algorithm == "scrypt"
    assert parsed.parameters == {
        "N": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "dklen": SCRYPT_DKLEN,
    }
    assert len(parsed.salt) == SALT_LENGTH
    assert len(parsed.digest) == SCRYPT_DKLEN
    assert hasher.verify(stored, PASSWORD)
    assert not hasher.verify(stored, WRONG_PASSWORD)
    assert not hasher.needs_rehash(stored)
    assert SCRYPT_MAXMEM > 128 * 1024 * 1024


def test_scrypt_is_used_when_argon2_dependency_is_missing() -> None:
    with patch("importlib.util.find_spec", return_value=None):
        hasher = PasswordHasher(prefer="auto")

    assert hasher.algorithm == "scrypt"


def test_missing_hashing_dependency_fails_closed() -> None:
    with (
        patch("importlib.util.find_spec", return_value=None),
        patch.object(PasswordHasher, "_scrypt_available", return_value=False),
        pytest.raises(PasswordHashingError),
    ):
        PasswordHasher(prefer="auto")

    with patch("importlib.util.find_spec", return_value=None), pytest.raises(PasswordHashingError):
        PasswordHasher(prefer="argon2id")


def test_verification_fails_closed_for_unsupported_stored_algorithm() -> None:
    argon2 = PasswordHasher(prefer="argon2id")
    scrypt = PasswordHasher(prefer="scrypt")

    argon2_hash = argon2.hash(PASSWORD)
    assert not scrypt.verify(argon2_hash, PASSWORD)
    assert scrypt.needs_rehash(argon2_hash)


def test_invalid_preference_is_rejected() -> None:
    with pytest.raises(PasswordHashingError):
        PasswordHasher(prefer="md5")


def test_hashlib_scrypt_presence_is_detected() -> None:
    assert hasattr(hashlib, "scrypt")
