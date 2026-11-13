"""Generate the application style sheet from design tokens."""

from __future__ import annotations

from string import Template

from app.ui.themes.tokens import FONT_FAMILY, METRICS, MONO_FONT_FAMILY, Metrics, Palette

_QSS_TEMPLATE = Template(
    """
* {
    outline: none;
}

QMainWindow,
QWidget#CentralWidget,
QWidget#ContentArea,
QStackedWidget {
    background-color: $bg_app;
}

QWidget {
    color: $text_primary;
    font-family: $font_family;
    font-size: 13px;
}

QLabel {
    background-color: transparent;
}

QLabel#PageTitle {
    font-size: 20px;
    font-weight: 600;
}

QLabel#PageSubtitle,
QLabel#MetaLabel {
    color: $text_secondary;
    font-size: 12px;
}

QLabel#SectionTitle {
    font-size: 15px;
    font-weight: 600;
}

QLabel#KpiValue {
    font-family: $mono_font_family;
    font-size: 26px;
    font-weight: 600;
}

QLabel#BrandTitle {
    font-size: 15px;
    font-weight: 600;
}

QLabel#BrandSubtitle {
    color: $text_secondary;
    font-size: 12px;
}

QLabel#NavGroupLabel {
    color: $text_secondary;
    font-size: 11px;
    font-weight: 600;
    padding: 10px 12px 4px 12px;
}

QLabel#FieldLabel {
    color: $text_secondary;
    font-size: 12px;
    font-weight: 500;
}

QFrame#Sidebar {
    background-color: $bg_surface;
    border-right: 1px solid $border_default;
}

QFrame#Sidebar QWidget,
QFrame#Sidebar QScrollArea,
QFrame#Sidebar QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QFrame#TopBar {
    background-color: $bg_surface;
    border-bottom: 1px solid $border_default;
}

QFrame#Divider {
    background-color: $border_default;
    max-height: 1px;
    min-height: 1px;
}

QFrame[card="true"] {
    background-color: $bg_surface;
    border: 1px solid $border_default;
    border-radius: ${radius_card}px;
}

QFrame[card="true"] QLabel {
    background-color: transparent;
}

QToolButton[nav="true"] {
    background-color: transparent;
    color: $text_primary;
    text-align: left;
    border: none;
    border-left: 3px solid transparent;
    border-radius: ${radius_input}px;
    padding: 7px 10px 7px 9px;
    min-height: 18px;
    font-size: 13px;
}

QToolButton[nav="true"]:hover {
    background-color: $bg_surface_alt;
}

QToolButton[nav="true"]:checked {
    background-color: $bg_selected;
    color: $primary;
    border-left: 3px solid $primary;
    font-weight: 600;
}

QToolButton[nav="true"]:focus {
    border: 1px solid $focus;
    border-left: 3px solid $primary;
}

QPushButton {
    background-color: $primary;
    color: $on_primary;
    border: 1px solid $primary;
    border-radius: ${radius_input}px;
    padding: 6px 14px;
    min-height: 18px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: $primary_hover;
    border-color: $primary_hover;
}

QPushButton:pressed {
    background-color: $primary_pressed;
    border-color: $primary_pressed;
}

QPushButton:focus {
    border: 2px solid $focus;
}

QPushButton:disabled {
    background-color: $bg_surface_alt;
    border-color: $border_default;
    color: $text_disabled;
}

QToolButton#ThemeButton {
    background-color: transparent;
    color: $text_primary;
    border: 1px solid $border_strong;
    border-radius: ${radius_input}px;
    padding: 6px 12px;
    min-height: 18px;
}

QToolButton#ThemeButton:hover {
    background-color: $bg_surface_alt;
}

QToolButton#ThemeButton:focus {
    border: 2px solid $focus;
}

QStatusBar {
    background-color: $bg_surface;
    border-top: 1px solid $border_default;
    color: $text_secondary;
    min-height: 24px;
}

QStatusBar QLabel {
    color: $text_secondary;
    font-size: 12px;
    padding: 0 6px;
}

QStatusBar::item {
    border: none;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QToolTip {
    background-color: $bg_surface;
    color: $text_primary;
    border: 1px solid $border_strong;
    border-radius: ${radius_input}px;
    padding: 4px 6px;
}

QMessageBox {
    background-color: $bg_surface;
}

QMessageBox QLabel {
    color: $text_primary;
}

QMessageBox QPushButton {
    min-width: 72px;
}
"""
)


def build_stylesheet(palette: Palette, metrics: Metrics = METRICS) -> str:
    """Return the QSS for ``palette`` with all tokens substituted."""
    return _QSS_TEMPLATE.substitute(
        bg_app=palette.bg_app,
        bg_surface=palette.bg_surface,
        bg_surface_alt=palette.bg_surface_alt,
        bg_selected=palette.bg_selected,
        border_default=palette.border_default,
        border_strong=palette.border_strong,
        text_primary=palette.text_primary,
        text_secondary=palette.text_secondary,
        text_disabled=palette.text_disabled,
        primary=palette.primary,
        primary_hover=palette.primary_hover,
        primary_pressed=palette.primary_pressed,
        on_primary=palette.on_primary,
        success=palette.success,
        warning=palette.warning,
        danger=palette.danger,
        info=palette.info,
        focus=palette.focus,
        font_family=FONT_FAMILY,
        mono_font_family=MONO_FONT_FAMILY,
        radius_input=metrics.radius_input,
        radius_card=metrics.radius_card,
        radius_dialog=metrics.radius_dialog,
    )
