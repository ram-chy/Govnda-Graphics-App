"""Repositories for customer/supplier master records."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.party import Party, PartyKind, normalize_phone, party_name_key
from app.infrastructure.database.models.party import PartyRecord

Clock = Callable[[], str]


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def to_domain(record: PartyRecord) -> Party:
    return Party(
        party_id=record.id,
        kind=PartyKind(record.party_kind),
        name=record.name,
        phone=record.phone,
        email=record.email,
        address=record.address,
        contact_person=record.contact_person,
        notes=record.notes,
        is_active=bool(record.is_active),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class PartyRepository:
    """Persistence for party master data without business-rule enforcement."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def get(self, party_id: int) -> Party | None:
        record = self._session.get(PartyRecord, party_id)
        return to_domain(record) if record is not None else None

    def list(
        self,
        kind: PartyKind,
        *,
        search: str = "",
        include_inactive: bool = True,
    ) -> tuple[Party, ...]:
        stmt = select(PartyRecord).where(PartyRecord.party_kind == kind.value)
        if not include_inactive:
            stmt = stmt.where(PartyRecord.is_active.is_(True))
        needle = " ".join(search.strip().split()).casefold()
        if needle:
            like = f"%{needle}%"
            stmt = stmt.where(
                or_(
                    func.lower(PartyRecord.name).like(like),
                    func.lower(PartyRecord.phone).like(like),
                    func.lower(PartyRecord.email).like(like),
                    func.lower(PartyRecord.contact_person).like(like),
                    func.lower(PartyRecord.address).like(like),
                )
            )
        stmt = stmt.order_by(
            PartyRecord.is_active.desc(),
            func.lower(PartyRecord.name),
            PartyRecord.id,
        )
        return tuple(to_domain(r) for r in self._session.scalars(stmt).all())

    def find_name_duplicates(
        self,
        kind: PartyKind,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> tuple[Party, ...]:
        key = party_name_key(name)
        stmt = select(PartyRecord).where(
            PartyRecord.party_kind == kind.value,
            PartyRecord.name_key == key,
        )
        if exclude_id is not None:
            stmt = stmt.where(PartyRecord.id != exclude_id)
        return tuple(to_domain(r) for r in self._session.scalars(stmt).all())

    def find_phone_duplicates(
        self,
        kind: PartyKind,
        phone: str,
        *,
        exclude_id: int | None = None,
    ) -> tuple[Party, ...]:
        normalized = normalize_phone(phone)
        if not normalized:
            return ()
        stmt = select(PartyRecord).where(
            PartyRecord.party_kind == kind.value,
            PartyRecord.phone == normalized,
            PartyRecord.is_active.is_(True),
        )
        if exclude_id is not None:
            stmt = stmt.where(PartyRecord.id != exclude_id)
        return tuple(to_domain(r) for r in self._session.scalars(stmt).all())

    def create(self, party: Party) -> Party:
        timestamp = self._clock()
        record = PartyRecord(
            party_kind=party.kind.value,
            name=party.name,
            name_key=party.name_key,
            phone=party.phone,
            email=party.email,
            address=party.address,
            contact_person=party.contact_person,
            notes=party.notes,
            is_active=bool(party.is_active),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(record)
        self._session.flush()
        return to_domain(record)

    def update(self, party: Party) -> Party:
        if party.party_id is None:
            raise ValueError("party_id is required for update")
        record = self._session.get(PartyRecord, party.party_id)
        if record is None:
            raise ValueError(f"Party {party.party_id} not found")
        record.name = party.name
        record.name_key = party.name_key
        record.phone = party.phone
        record.email = party.email
        record.address = party.address
        record.contact_person = party.contact_person
        record.notes = party.notes
        record.is_active = bool(party.is_active)
        record.updated_at = self._clock()
        self._session.flush()
        return to_domain(record)


__all__ = ["PartyRepository", "to_domain"]
