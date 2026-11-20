"""QtCore-only view model for the Business Profile settings page."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.domain.business_profile import (
    PROFILE_FIELDS,
    BusinessProfile,
    ProfileCompletion,
    ProfileVersion,
    assess_completion,
)
from app.services.business_profile_service import (
    BusinessProfileService,
    BusinessProfileServiceFactory,
)

ServiceFactory = Callable[[], BusinessProfileService | None]


@dataclass(frozen=True, slots=True)
class BusinessProfileSnapshot:
    available: bool
    unavailable_reason: str
    profile: BusinessProfile | None
    completion: ProfileCompletion
    draft: BusinessProfile
    field_errors: dict[str, str]
    is_dirty: bool
    versions: tuple[ProfileVersion, ...]
    logo_preview_path: Path | None
    pending_logo_path: Path | None
    selected_version: int | None


class BusinessProfileViewModel(QObject):
    """Turn service results into renderable profile state without owning widgets."""

    snapshot_changed = Signal(object)
    status_message = Signal(str)
    save_succeeded = Signal(str)
    save_failed = Signal(str)

    def __init__(
        self,
        service_factory: ServiceFactory | BusinessProfileServiceFactory,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service_factory: ServiceFactory = (
            service_factory.build
            if isinstance(service_factory, BusinessProfileServiceFactory)
            else service_factory
        )
        self._snapshot: BusinessProfileSnapshot | None = None
        self._saved_profile: BusinessProfile | None = None
        self._draft = BusinessProfile()
        self._field_errors: dict[str, str] = {}
        self._versions: tuple[ProfileVersion, ...] = ()
        self._logo_preview_path: Path | None = None
        self._pending_logo_path: Path | None = None
        self._selected_version: int | None = None

    @property
    def snapshot(self) -> BusinessProfileSnapshot | None:
        return self._snapshot

    @property
    def is_dirty(self) -> bool:
        return self._snapshot.is_dirty if self._snapshot is not None else False

    def refresh(self) -> None:
        service = self._service_factory()
        if service is None:
            self._clear_navigation_state()
            self._emit_snapshot(
                available=False,
                unavailable_reason=(
                    "No business database and data root are open. "
                    "Set up or locate the business data first."
                ),
                profile=None,
                completion=assess_completion(None),
            )
            return
        result = service.load()
        self._saved_profile = result.profile
        self._draft = result.profile or BusinessProfile()
        self._field_errors = {}
        self._versions = result.versions
        self._logo_preview_path = result.logo_preview_path
        self._pending_logo_path = None
        self._selected_version = None
        self._emit_snapshot(
            available=True,
            unavailable_reason="",
            profile=result.profile,
            completion=result.completion,
        )

    def set_field(self, field: str, value: str) -> None:
        if field not in PROFILE_FIELDS:
            raise ValueError(f"unknown business profile field: {field!r}")
        self._draft = replace(self._draft, **{field: value})
        self._field_errors.pop(field, None)
        self._emit_current()

    def choose_logo(self, path: str | Path) -> None:
        candidate = Path(path)
        if not candidate.is_file():
            self._field_errors["logo"] = "The selected logo file could not be read."
            self._emit_current()
            return
        self._pending_logo_path = candidate
        self._logo_preview_path = candidate
        self._field_errors.pop("logo", None)
        self._emit_current()
        self.status_message.emit(f"Logo selected: {candidate.name}")

    def select_version(self, version_number: int) -> None:
        service = self._service_factory()
        version = next(
            (item for item in self._versions if item.version_number == version_number),
            None,
        )
        if service is None or version is None:
            return
        try:
            service.record_history_viewed(version_number)
        except (OSError, RuntimeError):
            self.status_message.emit("The history view could not be recorded.")
        self._draft = version.to_profile()
        self._pending_logo_path = service.resolve_logo(version.logo_reference)
        self._logo_preview_path = self._pending_logo_path
        self._field_errors = {}
        self._selected_version = version_number
        self._emit_current()
        self.status_message.emit(f"Showing profile version {version_number}. Save to restore it.")

    def field_error(self, field: str) -> str:
        return self._field_errors.get(field, "")

    def save(self) -> bool:
        service = self._service_factory()
        if service is None:
            self.save_failed.emit("No business database is open. The profile was not saved.")
            return False
        result = service.save(self._draft, logo_path=self._pending_logo_path)
        if not result.success:
            self._field_errors = dict(result.field_errors)
            if result.versions:
                self._versions = result.versions
            self._emit_current()
            self.save_failed.emit(result.message)
            return False
        self._saved_profile = result.profile
        self._draft = result.profile or BusinessProfile()
        self._field_errors = {}
        self._versions = result.versions
        self._logo_preview_path = result.logo_preview_path
        self._pending_logo_path = None
        self._selected_version = None
        self._emit_current()
        self.save_succeeded.emit(result.message)
        return True

    def reset(self) -> None:
        self._draft = self._saved_profile or BusinessProfile()
        self._field_errors = {}
        self._logo_preview_path = self._current_logo_path()
        self._pending_logo_path = None
        self._selected_version = None
        self._emit_current()
        self.status_message.emit("Unsaved changes discarded.")

    def _current_logo_path(self) -> Path | None:
        if self._pending_logo_path is not None:
            return self._pending_logo_path
        if self._saved_profile is None or not self._saved_profile.logo_reference:
            return None
        service = self._service_factory()
        return service.resolve_logo(self._saved_profile.logo_reference) if service else None

    def _clear_navigation_state(self) -> None:
        self._saved_profile = None
        self._draft = BusinessProfile()
        self._field_errors = {}
        self._versions = ()
        self._logo_preview_path = None
        self._pending_logo_path = None
        self._selected_version = None

    def _emit_current(
        self,
        *,
        profile: BusinessProfile | None = None,
        completion: ProfileCompletion | None = None,
    ) -> None:
        self._emit_snapshot(
            available=self._snapshot.available if self._snapshot is not None else True,
            unavailable_reason=(
                self._snapshot.unavailable_reason if self._snapshot is not None else ""
            ),
            profile=self._saved_profile if profile is None else profile,
            completion=assess_completion(self._draft)
            if completion is None
            else completion,
        )

    def _emit_snapshot(
        self,
        *,
        available: bool,
        unavailable_reason: str,
        profile: BusinessProfile | None,
        completion: ProfileCompletion,
    ) -> None:
        baseline = profile or BusinessProfile()
        snapshot = BusinessProfileSnapshot(
            available=available,
            unavailable_reason=unavailable_reason,
            profile=profile,
            completion=completion,
            draft=self._draft,
            field_errors=dict(self._field_errors),
            is_dirty=self._draft != baseline or self._pending_logo_path is not None,
            versions=self._versions,
            logo_preview_path=self._logo_preview_path,
            pending_logo_path=self._pending_logo_path,
            selected_version=self._selected_version,
        )
        self._snapshot = snapshot
        self.snapshot_changed.emit(snapshot)


__all__ = ["BusinessProfileSnapshot", "BusinessProfileViewModel"]
