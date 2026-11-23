"""Application service for the approved Business Profile requirements."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import ConfigService
from app.core.exceptions import AppError
from app.core.logging_config import new_correlation_id
from app.domain.audit import (
    PROFILE_ENTITY_TYPE,
    UNAUTHENTICATED_ACTOR,
    AuditEvent,
    ProfileAuditEventType,
)
from app.domain.auth import PermissionKey
from app.domain.business_profile import (
    PROFILE_FIELDS,
    BusinessProfile,
    ProfileCompletion,
    ProfileVersion,
    assess_completion,
    validate_profile,
)
from app.infrastructure.database.business_profile_repository import (
    AuditEventRepository,
    BusinessProfileRepository,
    BusinessProfileVersionRepository,
    to_domain,
)
from app.infrastructure.database.engine import Database
from app.infrastructure.filesystem.layout import DataRootLayout
from app.services.auth_services import AuthServices
from app.services.database_runtime import DatabaseRuntime
from app.services.logo_storage_service import LogoStorageService, StoredLogo

logger = logging.getLogger(__name__)

Clock = Callable[[], str]


@dataclass(frozen=True, slots=True)
class LoadProfileResult:
    profile: BusinessProfile | None
    completion: ProfileCompletion
    versions: tuple[ProfileVersion, ...]
    logo_preview_path: Path | None


@dataclass(frozen=True, slots=True)
class SaveProfileResult:
    success: bool
    profile: BusinessProfile | None
    completion: ProfileCompletion
    versions: tuple[ProfileVersion, ...]
    field_errors: dict[str, str]
    message: str
    logo_preview_path: Path | None


class BusinessProfileService:
    """Coordinate validation, logo storage, transactions, history, and audit."""

    def __init__(
        self,
        database: Database,
        logo_storage: LogoStorageService,
        *,
        clock: Clock | None = None,
        auth_services: AuthServices | None = None,
    ) -> None:
        self._database = database
        self._logo_storage = logo_storage
        self._clock = clock
        self._auth_services = auth_services

    def _actor(self) -> str:
        if self._auth_services is not None and self._auth_services.session.identity is not None:
            return self._auth_services.session.actor
        return UNAUTHENTICATED_ACTOR

    def _require(self, permission: PermissionKey) -> None:
        if self._auth_services is not None:
            self._auth_services.authorization.require(permission)

    def load(self) -> LoadProfileResult:
        with self._database.unit_of_work() as work:
            record = BusinessProfileRepository(work.session, clock=self._clock).load()
            profile = to_domain(record) if record is not None else None
            versions = BusinessProfileVersionRepository(work.session, clock=self._clock).list()
        return LoadProfileResult(
            profile=profile,
            completion=assess_completion(profile),
            versions=versions,
            logo_preview_path=self._logo_storage.resolve(profile.logo_reference)
            if profile is not None
            else None,
        )

    def history(self) -> tuple[ProfileVersion, ...]:
        with self._database.unit_of_work() as work:
            return BusinessProfileVersionRepository(work.session, clock=self._clock).list()

    def audit_events(self) -> tuple[AuditEvent, ...]:
        self._require(PermissionKey.AUDIT_VIEW)
        with self._database.unit_of_work() as work:
            return AuditEventRepository(work.session, clock=self._clock).list()

    def resolve_logo(self, reference: str) -> Path | None:
        return self._logo_storage.resolve(reference)

    def record_history_viewed(self, version_number: int) -> None:
        timestamp = self._clock() if self._clock is not None else _timestamp()
        event = AuditEvent(
            event_type=ProfileAuditEventType.HISTORY_VIEWED,
            entity_type=PROFILE_ENTITY_TYPE,
            entity_id=str(version_number),
            actor=self._actor(),
            created_at=timestamp,
            payload=json.dumps({"version": version_number}, separators=(",", ":")),
        )
        with self._database.unit_of_work() as work:
            AuditEventRepository(work.session, clock=self._clock).add(event)
            work.commit()

    def save(self, draft: BusinessProfile, *, logo_path: Path | None = None) -> SaveProfileResult:
        self._require(PermissionKey.SETTINGS_APPLICATION_UPDATE)
        profile = draft.normalized()
        stored_logo: StoredLogo | None = None
        try:
            current = self._load_current()
            if logo_path is None and not profile.logo_reference and current is not None:
                profile = replace(profile, logo_reference=current.logo_reference)
            if logo_path is not None:
                next_number = self._next_version_number(current)
                stored_logo = self._logo_storage.store(logo_path, version_number=next_number)
                profile = replace(profile, logo_reference=stored_logo.reference)

            validation = validate_profile(profile)
            if not validation.is_valid:
                if stored_logo is not None:
                    self._logo_storage.discard(stored_logo.absolute_path)
                return self._invalid_result(profile, validation.errors)

            changed_fields = self._changed_fields(current, profile, logo_path is not None)
            if not changed_fields:
                if stored_logo is not None:
                    self._logo_storage.discard(stored_logo.absolute_path)
                return self._unchanged_result(profile)

            next_number = self._next_version_number(current)
            profile = replace(profile, version_number=next_number)
            versions, saved = self._commit_profile(profile, changed_fields, logo_path is not None)
        except AppError as exc:
            if stored_logo is not None:
                self._logo_storage.discard(stored_logo.absolute_path)
            return self._failure_result(profile, exc.user_message)
        except (SQLAlchemyError, OSError) as exc:
            if stored_logo is not None:
                self._logo_storage.discard(stored_logo.absolute_path)
            correlation_id = new_correlation_id()
            logger.error(
                "Business profile save failed [%s] (%s)", correlation_id, type(exc).__name__
            )
            return self._failure_result(
                profile, f"The profile could not be saved. Reference: {correlation_id}"
            )

        if stored_logo is not None and saved.logo_reference != stored_logo.reference:
            self._logo_storage.discard(stored_logo.absolute_path)
        return SaveProfileResult(
            success=True,
            profile=saved,
            completion=assess_completion(saved),
            versions=versions,
            field_errors={},
            message="Business profile saved.",
            logo_preview_path=self._logo_storage.resolve(saved.logo_reference),
        )

    def _load_current(self) -> BusinessProfile | None:
        with self._database.unit_of_work() as work:
            record = BusinessProfileRepository(work.session, clock=self._clock).load()
            return to_domain(record) if record is not None else None

    def _next_version_number(self, current: BusinessProfile | None) -> int:
        versions = self.history()
        highest = max((version.version_number for version in versions), default=0)
        return max(highest, current.version_number if current is not None else 0) + 1

    def _changed_fields(
        self,
        current: BusinessProfile | None,
        profile: BusinessProfile,
        logo_selected: bool,
    ) -> tuple[str, ...]:
        if current is None:
            return (*PROFILE_FIELDS, "logo")
        changed = tuple(
            name for name in PROFILE_FIELDS if getattr(current, name) != getattr(profile, name)
        )
        if current.logo_reference != profile.logo_reference or logo_selected:
            return (*changed, "logo")
        return changed

    def _commit_profile(
        self,
        profile: BusinessProfile,
        changed_fields: tuple[str, ...],
        logo_changed: bool,
    ) -> tuple[tuple[ProfileVersion, ...], BusinessProfile]:
        timestamp = self._clock() if self._clock is not None else _timestamp()
        payload = json.dumps({"fields": sorted(changed_fields)}, separators=(",", ":"))
        events = [
            AuditEvent(
                event_type=(
                    ProfileAuditEventType.CREATED
                    if profile.version_number == 1
                    else ProfileAuditEventType.UPDATED
                ),
                entity_type=PROFILE_ENTITY_TYPE,
                entity_id="1",
                actor=self._actor(),
                created_at=timestamp,
                payload=payload,
            )
        ]
        if logo_changed:
            events.append(
                AuditEvent(
                    event_type=ProfileAuditEventType.LOGO_CHANGED,
                    entity_type=PROFILE_ENTITY_TYPE,
                    entity_id="1",
                    actor=self._actor(),
                    created_at=timestamp,
                    payload='{"field":"logo"}',
                )
            )
        with self._database.unit_of_work() as work:
            profile_repo = BusinessProfileRepository(work.session, clock=self._clock)
            version_repo = BusinessProfileVersionRepository(work.session, clock=self._clock)
            audit_repo = AuditEventRepository(work.session, clock=self._clock)
            record = profile_repo.save(profile)
            version_repo.add(profile)
            for event in events:
                audit_repo.add(event)
            work.commit()
            saved = to_domain(record)
            versions = version_repo.list()
        return versions, saved

    def _invalid_result(
        self, profile: BusinessProfile, errors: dict[str, str]
    ) -> SaveProfileResult:
        return SaveProfileResult(
            success=False,
            profile=None,
            completion=assess_completion(profile),
            versions=self.history(),
            field_errors=errors,
            message="Enter every required field before saving.",
            logo_preview_path=None,
        )

    def _failure_result(self, profile: BusinessProfile, message: str) -> SaveProfileResult:
        return SaveProfileResult(
            success=False,
            profile=None,
            completion=assess_completion(profile),
            versions=(),
            field_errors={},
            message=message,
            logo_preview_path=None,
        )

    def _unchanged_result(self, profile: BusinessProfile) -> SaveProfileResult:
        versions = self.history()
        return SaveProfileResult(
            success=True,
            profile=profile,
            completion=assess_completion(profile),
            versions=versions,
            field_errors={},
            message="No changes to save.",
            logo_preview_path=self._logo_storage.resolve(profile.logo_reference),
        )


class BusinessProfileServiceFactory:
    """Build the service from the current database and configured data root."""

    def __init__(
        self,
        config_service: ConfigService,
        runtime: DatabaseRuntime,
        *,
        clock: Clock | None = None,
        auth_services: AuthServices | None = None,
    ) -> None:
        self._config_service = config_service
        self._runtime = runtime
        self._clock = clock
        self._auth_services = auth_services

    def build(self) -> BusinessProfileService | None:
        database = self._runtime.database
        config = self._config_service.load()
        if database is None or not config.data_root:
            return None
        storage = LogoStorageService(DataRootLayout(Path(config.data_root)), clock=self._clock)
        return BusinessProfileService(
            database, storage, clock=self._clock, auth_services=self._auth_services
        )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "BusinessProfileService",
    "BusinessProfileServiceFactory",
    "LoadProfileResult",
    "SaveProfileResult",
]
