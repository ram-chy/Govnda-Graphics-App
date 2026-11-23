"""Application service for Customer and Supplier master data (Phase 9)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError, NotFoundError, ValidationError
from app.core.logging_config import new_correlation_id
from app.domain.audit import AuditEvent
from app.domain.auth import PermissionKey
from app.domain.party import (
    PARTY_ENTITY_TYPE,
    Party,
    PartyAuditEventType,
    PartyDuplicateWarning,
    PartyKind,
    validate_party,
)
from app.infrastructure.database.business_profile_repository import AuditEventRepository
from app.infrastructure.database.party_repository import PartyRepository
from app.services.auth_services import AuthServices
from app.services.database_runtime import DatabaseRuntime

logger = logging.getLogger(__name__)
Clock = Callable[[], str]


@dataclass(frozen=True, slots=True)
class PartySaveResult:
    success: bool
    party: Party | None
    warnings: tuple[PartyDuplicateWarning, ...]
    errors: tuple[str, ...]
    message: str


class PartyService:
    """Service-layer enforcement for party master operations."""

    def __init__(
        self,
        runtime: DatabaseRuntime,
        *,
        auth_services: AuthServices | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._runtime = runtime
        self._auth = auth_services
        self._clock = clock

    def _now(self) -> str:
        if self._clock is not None:
            return self._clock()
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _actor(self) -> str:
        if self._auth is not None and self._auth.session.identity is not None:
            return self._auth.session.actor
        return "system/unauthenticated"

    def _require(self, permission: PermissionKey) -> None:
        if self._auth is not None:
            self._auth.authorization.require(permission)

    def _database(self):
        db = self._runtime.database
        if db is None:
            raise AppError(
                "Database unavailable",
                user_message="The database is not available. Please restart the application.",
            )
        return db

    def list_parties(
        self,
        kind: PartyKind,
        *,
        search: str = "",
        include_inactive: bool = True,
    ) -> tuple[Party, ...]:
        self._require(PermissionKey.PARTY_VIEW)
        try:
            with self._database().unit_of_work() as work:
                return PartyRepository(work.session, clock=self._clock).list(
                    kind, search=search, include_inactive=include_inactive
                )
        except SQLAlchemyError as exc:
            cid = new_correlation_id()
            logger.error("Party list failed [%s] (%s)", cid, type(exc).__name__)
            raise AppError(
                "Party list failed",
                user_message=f"Could not load {kind.label.lower()}s. Reference: {cid}",
            ) from exc

    def get_party(self, party_id: int) -> Party:
        self._require(PermissionKey.PARTY_VIEW)
        with self._database().unit_of_work() as work:
            party = PartyRepository(work.session, clock=self._clock).get(party_id)
        if party is None:
            raise NotFoundError(
                f"Party {party_id} not found",
                user_message="The selected record could not be found.",
            )
        return party

    def _duplicate_warnings(
        self, repo: PartyRepository, party: Party, *, exclude_id: int | None
    ) -> tuple[PartyDuplicateWarning, ...]:
        warnings: list[PartyDuplicateWarning] = []
        for existing in repo.find_name_duplicates(
            party.kind, party.name, exclude_id=exclude_id
        ):
            warnings.append(
                PartyDuplicateWarning(
                    reason=(
                        f"Another {party.kind.label.lower()} already has the same name: "
                        f"{existing.name}."
                    ),
                    existing_id=existing.party_id or 0,
                    existing_name=existing.name,
                )
            )
        for existing in repo.find_phone_duplicates(
            party.kind, party.phone, exclude_id=exclude_id
        ):
            warnings.append(
                PartyDuplicateWarning(
                    reason=(
                        f"Another active {party.kind.label.lower()} already uses this "
                        f"phone number: {existing.name}."
                    ),
                    existing_id=existing.party_id or 0,
                    existing_name=existing.name,
                )
            )
        # Deduplicate by (reason, existing_id)
        seen: set[tuple[str, int]] = set()
        unique: list[PartyDuplicateWarning] = []
        for w in warnings:
            key = (w.reason, w.existing_id)
            if key not in seen:
                seen.add(key)
                unique.append(w)
        return tuple(unique)

    def save_party(
        self,
        party: Party,
        *,
        confirm_duplicates: bool = False,
    ) -> PartySaveResult:
        is_create = party.party_id is None
        self._require(PermissionKey.PARTY_CREATE if is_create else PermissionKey.PARTY_EDIT)
        candidate = party.normalized()
        validation = validate_party(candidate)
        if not validation.valid:
            return PartySaveResult(False, None, (), validation.errors, validation.errors[0])

        try:
            with self._database().unit_of_work() as work:
                repo = PartyRepository(work.session, clock=self._clock)
                audit = AuditEventRepository(work.session, clock=self._clock)
                existing: Party | None = None
                if not is_create:
                    existing = repo.get(candidate.party_id)  # type: ignore[arg-type]
                    if existing is None:
                        raise NotFoundError(
                            f"Party {candidate.party_id} not found",
                            user_message="The selected record could not be found.",
                        )
                    if existing.kind != candidate.kind:
                        raise ValidationError(
                            "Party kind mismatch",
                            user_message="The record type cannot be changed.",
                        )

                warnings = self._duplicate_warnings(repo, candidate, exclude_id=candidate.party_id)
                if warnings and not confirm_duplicates:
                    return PartySaveResult(
                        False,
                        None,
                        warnings,
                        (),
                        "Possible duplicate found. Confirm to save anyway.",
                    )

                if is_create:
                    saved = repo.create(candidate)
                    events = [
                        AuditEvent(
                            event_type=PartyAuditEventType.CREATED.value,
                            entity_type=PARTY_ENTITY_TYPE,
                            entity_id=str(saved.party_id),
                            actor=self._actor(),
                            created_at=self._now(),
                            payload=json.dumps(
                                {
                                    "kind": saved.kind.value,
                                    "name": saved.name,
                                    "is_active": saved.is_active,
                                    "confirmed_duplicates": bool(warnings),
                                },
                                separators=(",", ":"),
                            ),
                        )
                    ]
                else:
                    assert existing is not None
                    # Preserve creation time; repository updates updated_at.
                    candidate = Party(
                        party_id=existing.party_id,
                        kind=existing.kind,
                        name=candidate.name,
                        phone=candidate.phone,
                        email=candidate.email,
                        address=candidate.address,
                        contact_person=candidate.contact_person,
                        notes=candidate.notes,
                        is_active=candidate.is_active,
                        created_at=existing.created_at,
                        updated_at=existing.updated_at,
                    )
                    saved = repo.update(candidate)
                    events = [
                        AuditEvent(
                            event_type=PartyAuditEventType.UPDATED.value,
                            entity_type=PARTY_ENTITY_TYPE,
                            entity_id=str(saved.party_id),
                            actor=self._actor(),
                            created_at=self._now(),
                            payload=json.dumps(
                                {
                                    "kind": saved.kind.value,
                                    "name": saved.name,
                                    "is_active": saved.is_active,
                                    "confirmed_duplicates": bool(warnings),
                                },
                                separators=(",", ":"),
                            ),
                        )
                    ]
                    if existing.is_active != saved.is_active:
                        events.append(
                            AuditEvent(
                                event_type=(
                                    PartyAuditEventType.ACTIVATED.value
                                    if saved.is_active
                                    else PartyAuditEventType.DEACTIVATED.value
                                ),
                                entity_type=PARTY_ENTITY_TYPE,
                                entity_id=str(saved.party_id),
                                actor=self._actor(),
                                created_at=self._now(),
                                payload=json.dumps(
                                    {"kind": saved.kind.value, "name": saved.name},
                                    separators=(",", ":"),
                                ),
                            )
                        )
                for event in events:
                    audit.add(event)
                work.commit()
                return PartySaveResult(
                    True,
                    saved,
                    warnings,
                    (),
                    f"{saved.kind.label} saved.",
                )
        except (AppError, ValidationError, NotFoundError):
            raise
        except SQLAlchemyError as exc:
            cid = new_correlation_id()
            logger.error("Party save failed [%s] (%s)", cid, type(exc).__name__)
            raise AppError(
                "Party save failed",
                user_message=f"The {party.kind.label.lower()} could not be saved. Reference: {cid}",
            ) from exc

    def set_active(self, party_id: int, *, active: bool) -> PartySaveResult:
        self._require(PermissionKey.PARTY_EDIT)
        party = self.get_party(party_id)
        if party.is_active == active:
            return PartySaveResult(True, party, (), (), "No change needed.")
        updated = Party(
            party_id=party.party_id,
            kind=party.kind,
            name=party.name,
            phone=party.phone,
            email=party.email,
            address=party.address,
            contact_person=party.contact_person,
            notes=party.notes,
            is_active=active,
            created_at=party.created_at,
            updated_at=party.updated_at,
        )
        return self.save_party(updated, confirm_duplicates=True)


class PartyServiceFactory:
    def __init__(
        self,
        runtime: DatabaseRuntime,
        *,
        auth_services: AuthServices | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._runtime = runtime
        self._auth_services = auth_services
        self._clock = clock

    def build(self) -> PartyService | None:
        if self._runtime.database is None:
            return None
        return PartyService(self._runtime, auth_services=self._auth_services, clock=self._clock)


__all__ = ["PartySaveResult", "PartyService", "PartyServiceFactory"]
