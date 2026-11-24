"""Design tokens for the light and dark themes.

Qt Style Sheets cannot use variables, so tokens live here and are substituted
into the QSS template. Custom-painted widgets must read the same tokens
(ADR-017, UI_UX_BLUEPRINT.md §9).

The palette values are the approved blueprint colors. Metrics and typography
are shared by both themes so every surface uses the same spacing rhythm.
"""

from __future__ import annotations

from dataclasses import dataclass

FONT_FAMILY = '"Segoe UI Variable Text", "Segoe UI", "Tahoma", sans-serif'
MONO_FONT_FAMILY = '"Cascadia Mono", "Consolas", monospace'

# Typography scale (UI_UX_BLUEPRINT.md §9.3). At most three weights are used on
# a single screen: 400 (body), 500 (fields), 600 (titles and KPIs).
FONT_SIZE_BODY = 15
FONT_SIZE_SMALL = 14
FONT_SIZE_MICRO = 13
FONT_SIZE_LABEL = 14
FONT_SIZE_SECTION = 17
FONT_SIZE_PAGE = 22
FONT_SIZE_KPI = 28
FONT_SIZE_WIZARD_TITLE = 24
LINE_HEIGHT_BODY = 22
LINE_HEIGHT_SMALL = 18
FONT_WEIGHT_REGULAR = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_SEMIBOLD = 600


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

    # Shell dimensions.
    sidebar_width: int = 240
    sidebar_compact_width: int = 48
    sidebar_collapse_threshold: int = 1360
    topbar_height: int = 56
    statusbar_height: int = 28
    window_default_width: int = 1440
    window_default_height: int = 900
    window_minimum_width: int = 1280
    window_minimum_height: int = 720

    # Controls and content.
    control_height: int = 36
    control_height_compact: int = 32
    table_row_height: int = 38
    icon_size: int = 16
    icon_size_nav: int = 20
    max_form_width: int = 760
    border_width: int = 1
    focus_ring_width: int = 2
    accent_bar_width: int = 3

    # Spacing scale (4, 8, 12, 16, 20, 24, 32, 40).
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 20
    space_6: int = 24
    space_7: int = 32
    space_8: int = 40

    # Shape.
    radius_input: int = 4
    radius_card: int = 6
    radius_dialog: int = 8

    # Content padding and dialog sizing.
    content_margin_horizontal: int = 24
    content_margin_vertical: int = 20
    dialog_width: int = 720
    dialog_minimum_width: int = 620
    dialog_height: int = 460
    dialog_minimum_height: int = 420
    dialog_button_min_width: int = 80
    wizard_width: int = 860
    wizard_minimum_width: int = 720
    wizard_height: int = 660
    wizard_minimum_height: int = 560


@dataclass(frozen=True, slots=True)
class ChartPalette:
    """Shared chart colors (UI_UX_BLUEPRINT.md §9.5).

    Charts are not drawn in this phase; the tokens are defined now so future
    chart cards do not introduce hardcoded colors.
    """

    series: tuple[str, ...]
    grid: str
    label: str
    background: str
    grid_opacity: int = 10


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

LIGHT_CHART_PALETTE = ChartPalette(
    series=("#1F7A4D", "#4F9083", "#C59A62", "#6C7F99", "#B47563"),
    grid="#5B6B62",
    label="#5B6B62",
    background="#FFFFFF",
)

DARK_CHART_PALETTE = ChartPalette(
    series=("#4CAF82", "#68B9A6", "#D0AC78", "#8EA4BE", "#D59080"),
    grid="#A3B0A8",
    label="#A3B0A8",
    background="#1A201D",
)

METRICS = Metrics()


def palette_for(dark: bool) -> Palette:
    return DARK_PALETTE if dark else LIGHT_PALETTE


def chart_palette_for(dark: bool) -> ChartPalette:
    return DARK_CHART_PALETTE if dark else LIGHT_CHART_PALETTE


__all__ = [
    "DARK_CHART_PALETTE",
    "DARK_PALETTE",
    "FONT_FAMILY",
    "FONT_SIZE_BODY",
    "FONT_SIZE_KPI",
    "FONT_SIZE_LABEL",
    "FONT_SIZE_MICRO",
    "FONT_SIZE_PAGE",
    "FONT_SIZE_SECTION",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_WIZARD_TITLE",
    "LIGHT_CHART_PALETTE",
    "LIGHT_PALETTE",
    "LINE_HEIGHT_BODY",
    "LINE_HEIGHT_SMALL",
    "METRICS",
    "MONO_FONT_FAMILY",
    "ChartPalette",
    "Metrics",
    "Palette",
    "chart_palette_for",
    "palette_for",
]
