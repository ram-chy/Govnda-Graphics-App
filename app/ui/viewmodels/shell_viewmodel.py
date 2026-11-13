"""Shell view model.

View models may use QtCore but never QtWidgets (ADR-004), which keeps them
testable without a window. This view model owns theme persistence and shell
status messages only.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from app.core.config import AppConfig, ConfigService
from app.core.exceptions import ConfigurationError
from app.domain.value_objects.currency import Currency

logger = logging.getLogger(__name__)


class ShellViewModel(QObject):
    """State shared by the main window and its header."""

    theme_preference_changed = Signal(str)
    status_message_changed = Signal(str)

    def __init__(
        self,
        config_service: ConfigService,
        config: AppConfig,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config_service = config_service
        self._config = config

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def currency(self) -> Currency:
        return self._config.currency

    @property
    def theme_preference(self) -> str:
        return self._config.theme

    @property
    def app_version(self) -> str:
        return self._config.app_version

    def set_theme_preference(self, preference: str) -> bool:
        """Persist a theme choice.

        The theme is applied by the caller before this method runs. A failed
        save is reported to the user and leaves the session usable.
        """
        try:
            updated = self._config.with_theme(preference)
        except (ConfigurationError, ValueError) as exc:
            logger.warning("Rejected theme preference %r: %s", preference, exc)
            self.status_message_changed.emit("The selected theme is not supported.")
            return False

        try:
            self._config_service.save(updated)
        except ConfigurationError:
            logger.exception("Theme preference could not be saved")
            self.status_message_changed.emit(
                "The theme changed for this session but could not be saved."
            )
            return False

        self._config = updated
        self.theme_preference_changed.emit(preference)
        self.status_message_changed.emit(
            f"Theme preference saved: {preference.replace('_', ' ').title()}."
        )
        return True
