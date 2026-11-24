"""Application service for Product and Service catalogue (Phase 10)."""

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
from app.domain.catalogue import (
    CATALOGUE_ENTITY_TYPE,
    CatalogueAuditEventType,
    CatalogueDuplicateWarning,
    CatalogueItem,
    CatalogueKind,
    validate_catalogue_item,
)
from app.infrastructure.database.business_profile_repository import AuditEventRepository
from app.infrastructure.database.catalogue_repository import CatalogueRepository
from app.services.auth_services import AuthServices
from app.services.database_runtime import DatabaseRuntime

logger = logging.getLogger(__name__)
Clock = Callable[[], str]


@dataclass(frozen=True, slots=True)
class CatalogueSaveResult:
    success: bool
    item: CatalogueItem | None
    warnings: tuple[CatalogueDuplicateWarning, ...]
    errors: tuple[str, ...]
    message: str


class CatalogueService:
    """Service-layer enforcement for catalogue operations."""

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

    def list_items(
        self,
        kind: CatalogueKind,
        *,
        search: str = "",
        include_inactive: bool = True,
    ) -> tuple[CatalogueItem, ...]:
        self._require(PermissionKey.CATALOGUE_VIEW)
        try:
            with self._database().unit_of_work() as work:
                return CatalogueRepository(work.session, clock=self._clock).list(
                    kind, search=search, include_inactive=include_inactive
                )
        except SQLAlchemyError as exc:
            cid = new_correlation_id()
            logger.error("Catalogue list failed [%s] (%s)", cid, type(exc).__name__)
            raise AppError(
                "Catalogue list failed",
                user_message=f"Could not load {kind.label.lower()}s. Reference: {cid}",
            ) from exc

    def get_item(self, item_id: int) -> CatalogueItem:
        self._require(PermissionKey.CATALOGUE_VIEW)
        with self._database().unit_of_work() as work:
            item = CatalogueRepository(work.session, clock=self._clock).get(item_id)
        if item is None:
            raise NotFoundError(
                f"Catalogue item {item_id} not found",
                user_message="The selected record could not be found.",
            )
        return item

    def _duplicate_warnings(
        self,
        repo: CatalogueRepository,
        item: CatalogueItem,
        *,
        exclude_id: int | None,
    ) -> tuple[CatalogueDuplicateWarning, ...]:
        warnings: list[CatalogueDuplicateWarning] = []
        for existing in repo.find_name_duplicates(
            item.kind, item.name, exclude_id=exclude_id
        ):
            warnings.append(
                CatalogueDuplicateWarning(
                    reason=(
                        f"Another {item.kind.label.lower()} already has the same name: "
                        f"{existing.name}."
                    ),
                    existing_id=existing.item_id or 0,
                    existing_name=existing.name,
                )
            )
        seen: set[tuple[str, int]] = set()
        unique: list[CatalogueDuplicateWarning] = []
        for w in warnings:
            key = (w.reason, w.existing_id)
            if key not in seen:
                seen.add(key)
                unique.append(w)
        return tuple(unique)

    def save_item(
        self,
        item: CatalogueItem,
        *,
        confirm_duplicates: bool = False,
    ) -> CatalogueSaveResult:
        is_create = item.item_id is None
        self._require(
            PermissionKey.CATALOGUE_CREATE if is_create else PermissionKey.CATALOGUE_EDIT
        )
        candidate = item.normalized()
        validation = validate_catalogue_item(candidate)
        if not validation.valid:
            return CatalogueSaveResult(False, None, (), validation.errors, validation.errors[0])

        try:
            with self._database().unit_of_work() as work:
                repo = CatalogueRepository(work.session, clock=self._clock)
                audit = AuditEventRepository(work.session, clock=self._clock)
                existing: CatalogueItem | None = None
                if not is_create:
                    existing = repo.get(candidate.item_id)  # type: ignore[arg-type]
                    if existing is None:
                        raise NotFoundError(
                            f"Catalogue item {candidate.item_id} not found",
                            user_message="The selected record could not be found.",
                        )
                    if existing.kind != candidate.kind:
                        raise ValidationError(
                            "Catalogue kind mismatch",
                            user_message="The record type cannot be changed.",
                        )

                warnings = self._duplicate_warnings(
                    repo, candidate, exclude_id=candidate.item_id
                )
                if warnings and not confirm_duplicates:
                    return CatalogueSaveResult(
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
                            event_type=CatalogueAuditEventType.CREATED.value,
                            entity_type=CATALOGUE_ENTITY_TYPE,
                            entity_id=str(saved.item_id),
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
                    candidate = CatalogueItem(
                        item_id=existing.item_id,
                        kind=existing.kind,
                        name=candidate.name,
                        description=candidate.description,
                        unit=candidate.unit,
                        default_sale_price_minor=candidate.default_sale_price_minor,
                        is_active=candidate.is_active,
                        created_at=existing.created_at,
                        updated_at=existing.updated_at,
                    )
                    saved = repo.update(candidate)
                    events = [
                        AuditEvent(
                            event_type=CatalogueAuditEventType.UPDATED.value,
                            entity_type=CATALOGUE_ENTITY_TYPE,
                            entity_id=str(saved.item_id),
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
                                    CatalogueAuditEventType.ACTIVATED.value
                                    if saved.is_active
                                    else CatalogueAuditEventType.DEACTIVATED.value
                                ),
                                entity_type=CATALOGUE_ENTITY_TYPE,
                                entity_id=str(saved.item_id),
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
                return CatalogueSaveResult(
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
            logger.error("Catalogue save failed [%s] (%s)", cid, type(exc).__name__)
            raise AppError(
                "Catalogue save failed",
                user_message=(
                    f"The {item.kind.label.lower()} could not be saved. Reference: {cid}"
                ),
            ) from exc

    def set_active(self, item_id: int, *, active: bool) -> CatalogueSaveResult:
        self._require(PermissionKey.CATALOGUE_EDIT)
        item = self.get_item(item_id)
        if item.is_active == active:
            return CatalogueSaveResult(True, item, (), (), "No change needed.")
        updated = CatalogueItem(
            item_id=item.item_id,
            kind=item.kind,
            name=item.name,
            description=item.description,
            unit=item.unit,
            default_sale_price_minor=item.default_sale_price_minor,
            is_active=active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        return self.save_item(updated, confirm_duplicates=True)


class CatalogueServiceFactory:
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

    def build(self) -> CatalogueService | None:
        if self._runtime.database is None:
            return None
        return CatalogueService(
            self._runtime, auth_services=self._auth_services, clock=self._clock
        )


__all__ = ["CatalogueSaveResult", "CatalogueService", "CatalogueServiceFactory"]
