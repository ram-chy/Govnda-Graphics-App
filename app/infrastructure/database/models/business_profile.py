"""Mapped records for the approved business-profile schema."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class BusinessProfileRecord(Base):
    __tablename__ = "business_profile"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    secondary_phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    website: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    footer_message: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    logo_reference: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    version_number: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class BusinessProfileVersionRecord(Base):
    __tablename__ = "business_profile_versions"
    IMMUTABLE = True
    __table_args__ = (
        CheckConstraint("profile_id = 1", name="single_profile_versions"),
        CheckConstraint("version_number > 0", name="positive_version"),
        UniqueConstraint("profile_id", "version_number", name="unique_profile_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("business_profile.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    secondary_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    footer_message: Mapped[str] = mapped_column(String(500), nullable=False)
    logo_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    IMMUTABLE = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[str] = mapped_column(String(2000), nullable=False, default="{}")


__all__ = ["AuditEventRecord", "BusinessProfileRecord", "BusinessProfileVersionRecord"]
