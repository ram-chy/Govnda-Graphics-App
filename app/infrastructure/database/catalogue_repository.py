"""Repositories for product/service catalogue master records."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.catalogue import (
    CatalogueItem,
    CatalogueKind,
    catalogue_name_key,
)
from app.infrastructure.database.models.catalogue import CatalogueItemRecord

Clock = Callable[[], str]


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def to_domain(record: CatalogueItemRecord) -> CatalogueItem:
    return CatalogueItem(
        item_id=record.id,
        kind=CatalogueKind(record.kind),
        name=record.name,
        description=record.description,
        unit=record.unit,
        default_sale_price_minor=record.default_sale_price_minor,
        is_active=bool(record.is_active),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class CatalogueRepository:
    """Persistence for catalogue master data without business-rule enforcement."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def get(self, item_id: int) -> CatalogueItem | None:
        record = self._session.get(CatalogueItemRecord, item_id)
        return to_domain(record) if record is not None else None

    def list(
        self,
        kind: CatalogueKind,
        *,
        search: str = "",
        include_inactive: bool = True,
    ) -> tuple[CatalogueItem, ...]:
        stmt = select(CatalogueItemRecord).where(CatalogueItemRecord.kind == kind.value)
        if not include_inactive:
            stmt = stmt.where(CatalogueItemRecord.is_active.is_(True))
        needle = " ".join(search.strip().split()).casefold()
        if needle:
            like = f"%{needle}%"
            stmt = stmt.where(
                or_(
                    func.lower(CatalogueItemRecord.name).like(like),
                    func.lower(CatalogueItemRecord.description).like(like),
                    func.lower(CatalogueItemRecord.unit).like(like),
                )
            )
        stmt = stmt.order_by(
            CatalogueItemRecord.is_active.desc(),
            func.lower(CatalogueItemRecord.name),
            CatalogueItemRecord.id,
        )
        return tuple(to_domain(r) for r in self._session.scalars(stmt).all())

    def find_name_duplicates(
        self,
        kind: CatalogueKind,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> tuple[CatalogueItem, ...]:
        key = catalogue_name_key(name)
        stmt = select(CatalogueItemRecord).where(
            CatalogueItemRecord.kind == kind.value,
            CatalogueItemRecord.name_key == key,
        )
        if exclude_id is not None:
            stmt = stmt.where(CatalogueItemRecord.id != exclude_id)
        return tuple(to_domain(r) for r in self._session.scalars(stmt).all())

    def create(self, item: CatalogueItem) -> CatalogueItem:
        timestamp = self._clock()
        record = CatalogueItemRecord(
            kind=item.kind.value,
            name=item.name,
            name_key=item.name_key,
            description=item.description,
            unit=item.unit,
            default_sale_price_minor=item.default_sale_price_minor,
            is_active=bool(item.is_active),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(record)
        self._session.flush()
        return to_domain(record)

    def update(self, item: CatalogueItem) -> CatalogueItem:
        if item.item_id is None:
            raise ValueError("item_id is required for update")
        record = self._session.get(CatalogueItemRecord, item.item_id)
        if record is None:
            raise ValueError(f"Catalogue item {item.item_id} not found")
        record.name = item.name
        record.name_key = item.name_key
        record.description = item.description
        record.unit = item.unit
        record.default_sale_price_minor = item.default_sale_price_minor
        record.is_active = bool(item.is_active)
        record.updated_at = self._clock()
        self._session.flush()
        return to_domain(record)


__all__ = ["CatalogueRepository", "to_domain"]
