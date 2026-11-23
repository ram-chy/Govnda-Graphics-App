"""Security infrastructure for password storage."""

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
)

__all__ = [
    "ARGON2_MEMORY_COST_KIB",
    "ARGON2_PARALLELISM",
    "ARGON2_TIME_COST",
    "PASSWORD_HASH_PARAMETERS",
    "SALT_LENGTH",
    "SCRYPT_DKLEN",
    "SCRYPT_MAXMEM",
    "SCRYPT_N",
    "SCRYPT_P",
    "SCRYPT_R",
    "PasswordHasher",
]

PASSWORD_HASH_PARAMETERS = (
    f"argon2id t={ARGON2_TIME_COST} m={ARGON2_MEMORY_COST_KIB}KiB "
    f"p={ARGON2_PARALLELISM}; scrypt N={SCRYPT_N} r={SCRYPT_R} p={SCRYPT_P} "
    f"dklen={SCRYPT_DKLEN} maxmem={SCRYPT_MAXMEM}"
)
