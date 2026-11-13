"""Runtime light/dark theme switching (ADR-017)."""

from __future__ import annotations

import logging
from enum import StrEnum

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.ui.themes.qss import build_stylesheet
from app.ui.themes.tokens import DARK_PALETTE, LIGHT_PALETTE, Palette, palette_for

logger = logging.getLogger(__name__)


class ThemeMode(StrEnum):
    """User theme preference, including following the Windows setting."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """Apply the QSS and Qt palette for the active theme.

    ``preference`` is what the user chose; ``is_dark`` is the effective result
    after resolving the system theme.
    """

    changed = Signal(str, bool)

    def __init__(self, application: QApplication, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._application = application
        self._preference = ThemeMode.SYSTEM
        self._is_dark = False

        style_hints = application.styleHints()
        if hasattr(style_hints, "colorSchemeChanged"):
            style_hints.colorSchemeChanged.connect(self._on_system_color_scheme_changed)

    @property
    def preference(self) -> ThemeMode:
        return self._preference

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def apply(self, preference: str | ThemeMode) -> None:
        """Apply a preference value and repaint all existing windows."""
        try:
            mode = ThemeMode(preference)
        except ValueError as exc:
            raise ValueError(f"unsupported theme preference: {preference!r}") from exc

        self._preference = mode
        self._apply_effective_theme()

    def toggle(self) -> ThemeMode:
        """Switch between explicit light and dark based on the visible theme."""
        target = ThemeMode.LIGHT if self._is_dark else ThemeMode.DARK
        self.apply(target)
        return target

    def _on_system_color_scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        if self._preference is ThemeMode.SYSTEM:
            self._apply_effective_theme()

    def _system_prefers_dark(self) -> bool:
        try:
            return self._application.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except AttributeError:  # pragma: no cover - older Qt without colorScheme()
            return False

    def _apply_effective_theme(self) -> None:
        is_dark = self._preference is ThemeMode.DARK or (
            self._preference is ThemeMode.SYSTEM and self._system_prefers_dark()
        )
        palette = palette_for(is_dark)

        self._application.setStyleSheet(build_stylesheet(palette))
        self._application.setPalette(_qt_palette(palette))
        self._is_dark = is_dark
        logger.debug("Applied %s theme (preference=%s)", palette.name, self._preference.value)
        self.changed.emit(self._preference.value, is_dark)


def _color(value: str) -> QColor:
    color = QColor(value)
    if not color.isValid():
        raise ValueError(f"invalid theme color: {value!r}")
    return color


def _qt_palette(palette: Palette) -> QPalette:
    """Build a Qt palette so native dialogs match the QSS theme."""
    qt_palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: palette.bg_app,
        QPalette.ColorRole.WindowText: palette.text_primary,
        QPalette.ColorRole.Base: palette.bg_surface,
        QPalette.ColorRole.AlternateBase: palette.bg_surface_alt,
        QPalette.ColorRole.Text: palette.text_primary,
        QPalette.ColorRole.Button: palette.bg_surface,
        QPalette.ColorRole.ButtonText: palette.text_primary,
        QPalette.ColorRole.BrightText: palette.on_primary,
        QPalette.ColorRole.Highlight: palette.primary,
        QPalette.ColorRole.HighlightedText: palette.on_primary,
        QPalette.ColorRole.ToolTipBase: palette.bg_surface,
        QPalette.ColorRole.ToolTipText: palette.text_primary,
        QPalette.ColorRole.PlaceholderText: palette.text_secondary,
        QPalette.ColorRole.Link: palette.info,
        QPalette.ColorRole.Mid: palette.border_default,
        QPalette.ColorRole.Dark: palette.border_strong,
    }
    for role, value in roles.items():
        qt_palette.setColor(role, _color(value))

    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        qt_palette.setColor(
            QPalette.ColorGroup.Disabled,
            role,
            _color(palette.text_disabled),
        )

    qt_palette.setColor(QPalette.ColorRole.Window, _color(palette.bg_app))
    return qt_palette


__all__ = ["DARK_PALETTE", "LIGHT_PALETTE", "ThemeManager", "ThemeMode"]
