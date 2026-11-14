"""View model for the first-launch setup wizard.

The view model may use QtCore but never QtWidgets (ADR-004). It owns validation
state and summary values; the wizard only renders them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.core.config import AppConfig
from app.infrastructure.filesystem.validation import LocationValidationResult
from app.services.setup_service import SetupService


@dataclass(frozen=True, slots=True)
class SetupSummary:
    """The values shown to the user before explicit confirmation."""

    data_root: Path
    database_path: Path
    drive_description: str
    warnings: tuple[str, ...]
    existing_database: bool


class SetupViewModel(QObject):
    """Hold the selected path and its latest validation result."""

    validation_changed = Signal(object)
    location_changed = Signal(str)

    def __init__(
        self,
        service: SetupService,
        base_config: AppConfig,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._base_config = base_config
        self._location = ""
        self._validation: LocationValidationResult | None = None

    @property
    def service(self) -> SetupService:
        return self._service

    @property
    def base_config(self) -> AppConfig:
        return self._base_config

    @property
    def location(self) -> str:
        return self._location

    @property
    def validation(self) -> LocationValidationResult | None:
        return self._validation

    @property
    def can_continue(self) -> bool:
        return self._validation is not None and self._validation.is_valid

    def set_location(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned == self._location:
            return
        self._location = cleaned
        self._validation = None
        self.location_changed.emit(cleaned)

    def validate(self) -> LocationValidationResult:
        """Validate the current text and publish the result."""
        result = self._service.validate(self._location)
        self._validation = result
        self.validation_changed.emit(result)
        return result

    def summary(self) -> SetupSummary | None:
        """Return confirmation values, or ``None`` before successful validation."""
        result = self._validation
        if result is None or result.layout is None:
            return None
        drive = result.drive
        warnings = tuple(check.message for check in result.warnings)
        existing = any(
            check.key == "existing_database" and check.status.value == "warning"
            for check in result.checks
        )
        return SetupSummary(
            data_root=result.layout.root,
            database_path=result.layout.database_path,
            drive_description=drive.describe() if drive is not None else "Drive not identified",
            warnings=warnings,
            existing_database=existing,
        )

    def directory_plan(self) -> tuple[tuple[Path, str], ...]:
        """Return the proposed directory list with purposes."""
        result = self._validation
        if result is None or result.layout is None:
            return ()
        return result.layout.directory_purposes()


__all__ = ["SetupSummary", "SetupViewModel"]
