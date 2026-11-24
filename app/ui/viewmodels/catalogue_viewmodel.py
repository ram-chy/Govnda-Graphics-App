"""QtCore-only view model for Product/Service catalogue screens."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, Signal

from app.core.exceptions import AppError
from app.domain.catalogue import CatalogueDuplicateWarning, CatalogueItem, CatalogueKind
from app.services.catalogue_service import CatalogueService, CatalogueServiceFactory


@dataclass(frozen=True, slots=True)
class CatalogueSnapshot:
    available: bool
    unavailable_reason: str
    kind: CatalogueKind
    items: tuple[CatalogueItem, ...]
    selected_id: int | None
    draft: CatalogueItem
    is_dirty: bool
    warnings: tuple[CatalogueDuplicateWarning, ...]
    errors: tuple[str, ...]
    search: str
    include_inactive: bool


class CatalogueViewModel(QObject):
    snapshot_changed = Signal(object)
    status_message = Signal(str)
    save_succeeded = Signal(str)
    save_failed = Signal(str)

    def __init__(
        self,
        kind: CatalogueKind,
        service_factory: CatalogueServiceFactory | object,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._kind = kind
        self._service_factory = service_factory
        self._snapshot: CatalogueSnapshot | None = None
        self._saved: CatalogueItem | None = None
        self._draft = CatalogueItem(item_id=None, kind=kind, name="")
        self._search = ""
        self._include_inactive = True
        self._warnings: tuple[CatalogueDuplicateWarning, ...] = ()
        self._errors: tuple[str, ...] = ()

    @property
    def kind(self) -> CatalogueKind:
        return self._kind

    @property
    def snapshot(self) -> CatalogueSnapshot | None:
        return self._snapshot

    def _service(self) -> CatalogueService | None:
        build = getattr(self._service_factory, "build", None)
        if callable(build):
            return build()
        return None

    def refresh(self) -> None:
        service = self._service()
        if service is None:
            self._emit(False, "The database is not available.", ())
            return
        try:
            items = service.list_items(
                self._kind, search=self._search, include_inactive=self._include_inactive
            )
        except AppError as exc:
            self._emit(False, exc.user_message, ())
            self.status_message.emit(exc.user_message)
            return
        self._emit(True, "", items)

    def set_search(self, value: str) -> None:
        self._search = value
        self.refresh()

    def set_include_inactive(self, value: bool) -> None:
        self._include_inactive = bool(value)
        self.refresh()

    def new_item(self) -> None:
        self._saved = None
        self._draft = CatalogueItem(item_id=None, kind=self._kind, name="")
        self._warnings = ()
        self._errors = ()
        self.refresh()
        self.status_message.emit(f"New {self._kind.label.lower()}.")

    def select(self, item_id: int) -> None:
        service = self._service()
        if service is None:
            return
        try:
            item = service.get_item(item_id)
        except AppError as exc:
            self.save_failed.emit(exc.user_message)
            return
        self._saved = item
        self._draft = item
        self._warnings = ()
        self._errors = ()
        self.refresh()

    def set_field(self, name: str, value: object) -> None:
        if not hasattr(self._draft, name):
            return
        self._draft = replace(self._draft, **{name: value})
        self._warnings = ()
        self._errors = ()
        self._emit_current()

    def save(self, *, confirm_duplicates: bool = False) -> bool:
        service = self._service()
        if service is None:
            self.save_failed.emit("The database is not available.")
            return False
        try:
            result = service.save_item(self._draft, confirm_duplicates=confirm_duplicates)
        except AppError as exc:
            self._errors = (exc.user_message,)
            self._emit_current()
            self.save_failed.emit(exc.user_message)
            return False
        self._warnings = result.warnings
        self._errors = result.errors
        if not result.success:
            self._emit_current()
            self.save_failed.emit(result.message)
            return False
        self._saved = result.item
        self._draft = result.item if result.item is not None else self._draft
        self.refresh()
        self.save_succeeded.emit(result.message)
        return True

    def set_active(self, active: bool) -> bool:
        service = self._service()
        if service is None or self._draft.item_id is None:
            return False
        try:
            result = service.set_active(self._draft.item_id, active=active)
        except AppError as exc:
            self._errors = (exc.user_message,)
            self._emit_current()
            self.save_failed.emit(exc.user_message)
            return False
        self._warnings = result.warnings
        self._errors = result.errors
        if not result.success:
            self._emit_current()
            self.save_failed.emit(result.message)
            return False
        self._saved = result.item
        self._draft = result.item if result.item is not None else self._draft
        self.refresh()
        self.save_succeeded.emit(result.message)
        return True

    def _emit_current(self) -> None:
        items = self._snapshot.items if self._snapshot is not None else ()
        available = self._snapshot.available if self._snapshot is not None else True
        reason = self._snapshot.unavailable_reason if self._snapshot is not None else ""
        self._emit(available, reason, items)

    def _emit(self, available: bool, reason: str, items: tuple[CatalogueItem, ...]) -> None:
        snapshot = CatalogueSnapshot(
            available=available,
            unavailable_reason=reason,
            kind=self._kind,
            items=items,
            selected_id=self._draft.item_id,
            draft=self._draft,
            is_dirty=self._saved != self._draft,
            warnings=self._warnings,
            errors=self._errors,
            search=self._search,
            include_inactive=self._include_inactive,
        )
        self._snapshot = snapshot
        self.snapshot_changed.emit(snapshot)
