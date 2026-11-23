"""SQLAlchemy models for Customer/Supplier master records."""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class PartyRecord(Base):
    __tablename__ = "parties"

    __table_args__ = (
        CheckConstraint("party_kind IN ('customer','supplier')", name="ck_parties_kind"),
        CheckConstraint("length(trim(name)) > 0", name="ck_parties_name_not_empty"),
        CheckConstraint("is_active IN (0, 1)", name="ck_parties_is_active_bool"),
        Index("ix_parties_kind_name_key", "party_kind", "name_key"),
        Index("ix_parties_kind_phone", "party_kind", "phone"),
        Index("ix_parties_kind_is_active", "party_kind", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    party_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_key: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    contact_person: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


__all__ = ["PartyRecord"]
