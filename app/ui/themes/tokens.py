"""Design tokens for the light and dark themes.

Qt Style Sheets cannot use variables, so tokens live here and are substituted
into the QSS template. Custom-painted widgets must read the same tokens
(ADR-017, UI_UX_BLUEPRINT.md §9).
"""

from __future__ import annotations

from dataclasses import dataclass

FONT_FAMILY = '"Segoe UI Variable Text", "Segoe UI", "Tahoma", sans-serif'
MONO_FONT_FAMILY = '"Cascadia Mono", "Consolas", monospace'


@dataclass(frozen=True, slots=True)
class Palette:
    """Named colors for one theme."""

    name: str
    is_dark: bool
    bg_app: str
    bg_surface: str
    bg_surface_alt: str
    bg_selected: str
    border_default: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    primary: str
    primary_hover: str
    primary_pressed: str
    on_primary: str
    success: str
    warning: str
    danger: str
    info: str
    focus: str


@dataclass(frozen=True, slots=True)
class Metrics:
    """Spacing, sizing, and shape tokens shared by both themes."""

    sidebar_width: int = 240
    topbar_height: int = 56
    control_height: int = 32
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 20
    space_6: int = 24
    radius_input: int = 4
    radius_card: int = 6
    radius_dialog: int = 8
    content_margin_horizontal: int = 24
    content_margin_vertical: int = 20


LIGHT_PALETTE = Palette(
    name="light",
    is_dark=False,
    bg_app="#F6F7F5",
    bg_surface="#FFFFFF",
    bg_surface_alt="#EEF2EE",
    bg_selected="#E3F1E8",
    border_default="#DDE3DD",
    border_strong="#C3CCC5",
    text_primary="#1B231F",
    text_secondary="#5B6B62",
    text_disabled="#93A099",
    primary="#1F7A4D",
    primary_hover="#18643F",
    primary_pressed="#124E31",
    on_primary="#FFFFFF",
    success="#2E7D32",
    warning="#B26A00",
    danger="#B3261E",
    info="#1D6FB8",
    focus="#2F8F63",
)

DARK_PALETTE = Palette(
    name="dark",
    is_dark=True,
    bg_app="#121614",
    bg_surface="#1A201D",
    bg_surface_alt="#232B27",
    bg_selected="#243B30",
    border_default="#313B35",
    border_strong="#44524A",
    text_primary="#E8EEE9",
    text_secondary="#A3B0A8",
    text_disabled="#6E7B73",
    primary="#4CAF82",
    primary_hover="#5CBF90",
    primary_pressed="#3E9A71",
    on_primary="#0E1512",
    success="#66BB6A",
    warning="#E0A64A",
    danger="#EF6B62",
    info="#64A9E8",
    focus="#6FD3A2",
)

METRICS = Metrics()


def palette_for(dark: bool) -> Palette:
    return DARK_PALETTE if dark else LIGHT_PALETTE
