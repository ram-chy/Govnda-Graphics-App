"""Repositories for profiles, immutable versions, and audit events."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.audit import AuditEvent
from app.domain.business_profile import (
    PROFILE_FIELDS,
    SINGLE_PROFILE_ID,
    BusinessProfile,
    ProfileVersion,
)
from app.infrastructure.database.models.business_profile import (
    AuditEventRecord,
    BusinessProfileRecord,
    BusinessProfileVersionRecord,
)

Clock = Callable[[], str]


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class BusinessProfileRepository:
    """Persist an already-validated current profile without applying rules."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def load(self) -> BusinessProfileRecord | None:
        return self._session.get(BusinessProfileRecord, SINGLE_PROFILE_ID)

    def save(self, profile: BusinessProfile) -> BusinessProfileRecord:
        record = self.load()
        timestamp = self._clock()
        if record is None:
            record = BusinessProfileRecord(
                id=SINGLE_PROFILE_ID, created_at=timestamp, updated_at=timestamp
            )
            self._session.add(record)
        else:
            record.updated_at = timestamp
        for name in (*PROFILE_FIELDS, "logo_reference"):
            setattr(record, name, getattr(profile, name))
        record.version_number = profile.version_number
        return record


class BusinessProfileVersionRepository:
    """Append-only access to immutable profile snapshots."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def add(self, profile: BusinessProfile) -> ProfileVersion:
        timestamp = self._clock()
        record = BusinessProfileVersionRecord(
            profile_id=SINGLE_PROFILE_ID,
            version_number=profile.version_number,
            business_name=profile.business_name,
            address=profile.address,
            phone=profile.phone,
            secondary_phone=profile.secondary_phone,
            email=profile.email,
            website=profile.website,
            registration_number=profile.registration_number,
            footer_message=profile.footer_message,
            logo_reference=profile.logo_reference,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(record)
        return to_version(record)

    def list(self) -> tuple[ProfileVersion, ...]:
        records = self._session.scalars(
            select(BusinessProfileVersionRecord)
            .where(BusinessProfileVersionRecord.profile_id == SINGLE_PROFILE_ID)
            .order_by(BusinessProfileVersionRecord.version_number)
        ).all()
        return tuple(to_version(record) for record in records)


class AuditEventRepository:
    """Append-only audit-event storage with no ordinary deletion path."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_timestamp

    def add(self, event: AuditEvent) -> AuditEventRecord:
        record = AuditEventRecord(
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            actor=event.actor,
            created_at=event.created_at or self._clock(),
            payload=event.payload,
        )
        self._session.add(record)
        return record

    def list(self) -> tuple[AuditEvent, ...]:
        records = self._session.scalars(
            select(AuditEventRecord).order_by(AuditEventRecord.id)
        ).all()
        return tuple(
            AuditEvent(
                event_type=record.event_type,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                actor=record.actor,
                created_at=record.created_at,
                payload=record.payload,
            )
            for record in records
        )


def to_domain(record: BusinessProfileRecord) -> BusinessProfile:
    return BusinessProfile(
        business_name=record.business_name,
        address=record.address,
        phone=record.phone,
        secondary_phone=record.secondary_phone,
        email=record.email,
        website=record.website,
        registration_number=record.registration_number,
        footer_message=record.footer_message,
        logo_reference=record.logo_reference,
        version_number=record.version_number,
    )


def to_version(record: BusinessProfileVersionRecord) -> ProfileVersion:
    return ProfileVersion(
        version_number=record.version_number,
        business_name=record.business_name,
        address=record.address,
        phone=record.phone,
        secondary_phone=record.secondary_phone,
        email=record.email,
        website=record.website,
        registration_number=record.registration_number,
        footer_message=record.footer_message,
        logo_reference=record.logo_reference,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


__all__ = [
    "AuditEventRepository",
    "BusinessProfileRepository",
    "BusinessProfileVersionRepository",
    "to_domain",
    "to_version",
]
