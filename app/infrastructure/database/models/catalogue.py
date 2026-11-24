"""SQLAlchemy model for Product/Service catalogue records."""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class CatalogueItemRecord(Base):
    __tablename__ = "catalogue_items"

    __table_args__ = (
        CheckConstraint(
            "kind IN ('product', 'service')",
            name="ck_catalogue_items_kind",
        ),
        CheckConstraint("length(trim(name)) > 0", name="ck_catalogue_items_name_not_empty"),
        CheckConstraint("is_active IN (0, 1)", name="ck_catalogue_items_is_active_bool"),
        CheckConstraint(
            "default_sale_price_minor IS NULL OR default_sale_price_minor >= 0",
            name="ck_catalogue_items_price_non_negative",
        ),
        Index("ix_catalogue_items_kind_name_key", "kind", "name_key"),
        Index("ix_catalogue_items_kind_is_active", "kind", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_key: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    unit: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    default_sale_price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


__all__ = ["CatalogueItemRecord"]
