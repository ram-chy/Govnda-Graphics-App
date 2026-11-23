"""Mapped records for local user accounts and approved roles."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class RoleRecord(Base):
    """Reference row for one of the four owner-approved roles."""

    __tablename__ = "roles"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)


class UserRecord(Base):
    """Local account row. Passwords are stored only as self-describing hashes."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("is_active IN (0, 1)", name="active_flag"),
        CheckConstraint(
            "role_key IN ('owner_admin', 'operator', 'accountant_reviewer', 'viewer')",
            name="approved_role",
        ),
        UniqueConstraint("username_key", name="case_insensitive_username"),
        Index("ix_users_role_key", "role_key"),
        Index("ix_users_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    username_key: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[int] = mapped_column(nullable=False, default=1)
    role_key: Mapped[str] = mapped_column(String(50), ForeignKey("roles.key"), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class LoginThrottleRecord(Base):
    """Persistent failed-login state so restarts cannot bypass the cooldown."""

    __tablename__ = "login_throttles"
    __table_args__ = (CheckConstraint("failed_count >= 0", name="non_negative_count"),)

    username_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    failed_count: Mapped[int] = mapped_column(nullable=False, default=0)
    first_failed_at: Mapped[str] = mapped_column(String(32), nullable=False)
    cooldown_until: Mapped[str | None] = mapped_column(String(32), nullable=True)


__all__ = ["LoginThrottleRecord", "RoleRecord", "UserRecord"]
