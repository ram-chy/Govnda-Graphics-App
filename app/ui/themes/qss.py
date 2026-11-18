"""Generate the application style sheet from design tokens.

No color, font family, font size, spacing step, or radius is hardcoded here.
Every visual value is a token supplied by :func:`build_stylesheet`
(ADR-017, UI_UX_BLUEPRINT.md §9).
"""

from __future__ import annotations

from dataclasses import asdict
from string import Template

from app.ui.themes import tokens
from app.ui.themes.tokens import Metrics, Palette

_QSS_TEMPLATE = Template(
    """
* {
    outline: none;
}

QMainWindow,
QWidget#CentralWidget,
QWidget#ContentArea,
QWidget#DashboardContent,
QWidget#BackupContent,
QStackedWidget,
QDialog {
    background-color: $bg_app;
}

QWidget {
    color: $text_primary;
    font-family: $font_family;
    font-size: ${font_size_body}px;
}

QLabel {
    background-color: transparent;
}

QLabel#PageTitle {
    font-size: ${font_size_page}px;
    font-weight: $font_weight_semibold;
}

QLabel#PageSubtitle,
QLabel#MetaLabel {
    color: $text_secondary;
    font-size: ${font_size_small}px;
}

QLabel#SectionTitle {
    font-size: ${font_size_section}px;
    font-weight: $font_weight_semibold;
}

QLabel#KpiValue {
    font-family: $mono_font_family;
    font-size: ${font_size_kpi}px;
    font-weight: $font_weight_semibold;
}

QLabel#InfoValue {
    font-size: ${font_size_page}px;
    font-weight: $font_weight_semibold;
}

QLabel#BrandTitle {
    font-size: ${font_size_section}px;
    font-weight: $font_weight_semibold;
}

QLabel#BrandSubtitle {
    color: $text_secondary;
    font-size: ${font_size_small}px;
}

QLabel#NavGroupLabel {
    color: $text_secondary;
    font-size: ${font_size_micro}px;
    font-weight: $font_weight_semibold;
    padding: ${space_3}px ${space_3}px ${space_1}px ${space_3}px;
}

QLabel#FieldLabel {
    color: $text_secondary;
    font-size: ${font_size_label}px;
    font-weight: $font_weight_medium;
}

QFrame#Sidebar {
    background-color: $bg_surface;
    border-right: ${border_width}px solid $border_default;
}

QFrame#Sidebar QWidget,
QFrame#Sidebar QScrollArea,
QFrame#Sidebar QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QFrame#TopBar {
    background-color: $bg_surface;
    border-bottom: ${border_width}px solid $border_default;
}

QFrame#Divider {
    background-color: $border_default;
    max-height: ${border_width}px;
    min-height: ${border_width}px;
}

QFrame[card="true"] {
    background-color: $bg_surface;
    border: ${border_width}px solid $border_default;
    border-radius: ${radius_card}px;
}

QFrame[card="true"] QLabel {
    background-color: transparent;
}

QFrame#Toast {
    border-left: ${accent_bar_width}px solid $primary;
    border-radius: ${radius_dialog}px;
}

QFrame#Toast[tone="warning"] {
    border-left: ${accent_bar_width}px dashed $warning;
}

QFrame#Toast[tone="error"] {
    border-left: ${accent_bar_width}px double $danger;
}

QFrame#Toast[tone="info"] {
    border-left: ${accent_bar_width}px dotted $info;
}

QFrame#WizardHeader,
QFrame#WizardFooter {
    background-color: $bg_surface;
}

QFrame#WizardHeader {
    border-bottom: ${border_width}px solid $border_default;
}

QFrame#WizardFooter {
    border-top: ${border_width}px solid $border_default;
}

QStackedWidget#WizardPages,
QWidget#WizardPage {
    background-color: $bg_app;
}

QToolButton {
    color: $text_primary;
    border: ${border_width}px solid transparent;
    border-radius: ${radius_input}px;
    padding: ${space_1}px ${space_3}px;
    min-height: ${control_height_compact}px;
}

QToolButton:hover {
    background-color: $bg_surface_alt;
}

QToolButton:focus {
    border: ${focus_ring_width}px solid $focus;
}

QToolButton[nav="true"] {
    background-color: transparent;
    color: $text_primary;
    text-align: left;
    border: none;
    border-left: ${accent_bar_width}px solid transparent;
    border-radius: ${radius_input}px;
    padding: ${space_2}px ${space_3}px;
    min-height: ${control_height}px;
    font-size: ${font_size_body}px;
}

QToolButton[nav="true"]:hover {
    background-color: $bg_surface_alt;
}

QToolButton[nav="true"]:checked {
    background-color: $bg_selected;
    color: $primary;
    border-left: ${accent_bar_width}px solid $primary;
    font-weight: $font_weight_semibold;
}

QToolButton[nav="true"]:focus {
    border: ${focus_ring_width}px solid $focus;
    border-left: ${accent_bar_width}px solid $primary;
}

QToolButton#ThemeButton {
    background-color: transparent;
    color: $text_primary;
    border: ${border_width}px solid $border_strong;
    border-radius: ${radius_input}px;
    padding: ${space_1}px ${space_3}px;
    min-height: ${control_height_compact}px;
}

QToolButton#ThemeButton:hover {
    background-color: $bg_surface_alt;
}

QToolButton#ThemeButton:pressed {
    background-color: $bg_selected;
}

QToolButton#ThemeButton:focus {
    border: ${focus_ring_width}px solid $focus;
}

QPushButton {
    background-color: $primary;
    color: $on_primary;
    border: ${border_width}px solid $primary;
    border-radius: ${radius_input}px;
    padding: ${space_1}px ${space_4}px;
    min-height: ${control_height_compact}px;
    font-weight: $font_weight_semibold;
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
    border: ${focus_ring_width}px solid $focus;
}

QPushButton:disabled {
    background-color: $bg_surface_alt;
    border-color: $border_default;
    color: $text_disabled;
}

QPushButton[secondary="true"] {
    background-color: transparent;
    color: $text_primary;
    border-color: $border_strong;
}

QPushButton[secondary="true"]:hover {
    background-color: $bg_surface_alt;
    border-color: $border_strong;
}

QPushButton[secondary="true"]:pressed {
    background-color: $bg_selected;
}

QPushButton[secondary="true"]:focus {
    border: ${focus_ring_width}px solid $focus;
}

QPushButton[secondary="true"]:disabled {
    background-color: transparent;
    color: $text_disabled;
    border-color: $border_default;
}

QPushButton[danger="true"] {
    background-color: transparent;
    color: $danger;
    border-color: $danger;
}

QPushButton[danger="true"]:hover {
    background-color: $danger;
    color: $on_primary;
}

QPushButton[danger="true"]:pressed {
    background-color: $danger;
    color: $on_primary;
}

QPushButton[danger="true"]:focus {
    border: ${focus_ring_width}px solid $focus;
}

QPushButton[danger="true"]:disabled {
    background-color: transparent;
    color: $text_disabled;
    border-color: $border_default;
}

QStatusBar {
    background-color: $bg_surface;
    border-top: ${border_width}px solid $border_default;
    color: $text_secondary;
    min-height: ${statusbar_height}px;
}

QStatusBar QLabel {
    color: $text_secondary;
    font-size: ${font_size_small}px;
    padding: 0 ${space_2}px;
}

QStatusBar::item {
    border: none;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background-color: $bg_surface_alt;
    width: ${space_3}px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: $border_strong;
    border-radius: ${radius_input}px;
    min-height: ${space_5}px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
    height: 0;
}

QScrollBar:horizontal {
    background-color: $bg_surface_alt;
    height: ${space_3}px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: $border_strong;
    border-radius: ${radius_input}px;
    min-width: ${space_5}px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
    width: 0;
}

QToolTip {
    background-color: $bg_surface;
    color: $text_primary;
    border: ${border_width}px solid $border_strong;
    border-radius: ${radius_input}px;
    padding: ${space_1}px ${space_2}px;
}

QMessageBox {
    background-color: $bg_surface;
}

QMessageBox QLabel {
    color: $text_primary;
}

QMessageBox QPushButton {
    min-width: ${dialog_button_min_width}px;
}

QLabel#WizardTitle {
    font-size: ${font_size_wizard_title}px;
    font-weight: $font_weight_semibold;
}

QLabel#WizardSubtitle {
    color: $text_secondary;
    font-size: ${font_size_body}px;
}

QLabel#WizardStep {
    color: $text_secondary;
    font-size: ${font_size_small}px;
    font-weight: $font_weight_semibold;
}

QLabel#WizardBody {
    font-size: ${font_size_body}px;
}

QLabel#WizardPath {
    font-family: $mono_font_family;
    font-size: ${font_size_small}px;
    background-color: $bg_surface_alt;
    border: ${border_width}px solid $border_default;
    border-radius: ${radius_input}px;
    padding: ${space_1}px ${space_2}px;
}

QLabel#WizardError {
    color: $danger;
    font-weight: $font_weight_semibold;
}

QLabel#WizardSuccess {
    color: $success;
    font-weight: $font_weight_semibold;
}

QLabel[checkStatus="pass"] {
    color: $success;
    font-weight: $font_weight_semibold;
    border-left: ${accent_bar_width}px solid $success;
    padding-left: ${space_2}px;
}

QLabel[checkStatus="warning"] {
    color: $warning;
    font-weight: $font_weight_semibold;
    border-left: ${accent_bar_width}px dashed $warning;
    padding-left: ${space_2}px;
}

QLabel[checkStatus="error"] {
    color: $danger;
    font-weight: $font_weight_semibold;
    border-left: ${accent_bar_width}px double $danger;
    padding-left: ${space_2}px;
}

QLabel[checkStatus="info"] {
    color: $info;
    font-weight: $font_weight_semibold;
    border-left: ${accent_bar_width}px dotted $info;
    padding-left: ${space_2}px;
}

QFrame[validationRow="true"] {
    background-color: $bg_surface;
    border: ${border_width}px solid $border_default;
    border-radius: ${radius_input}px;
}

QLineEdit,
QSpinBox,
QTimeEdit,
QComboBox {
    background-color: $bg_surface;
    color: $text_primary;
    border: ${border_width}px solid $border_strong;
    border-radius: ${radius_input}px;
    padding: ${space_1}px ${space_2}px;
    min-height: ${control_height_compact}px;
}

QLineEdit:focus,
QSpinBox:focus,
QTimeEdit:focus,
QComboBox:focus {
    border: ${focus_ring_width}px solid $focus;
}

QLineEdit:disabled,
QSpinBox:disabled,
QTimeEdit:disabled,
QComboBox:disabled {
    background-color: $bg_surface_alt;
    color: $text_disabled;
}

QSpinBox::up-button,
QSpinBox::down-button,
QTimeEdit::up-button,
QTimeEdit::down-button {
    width: ${space_4}px;
    border: none;
    background-color: transparent;
}

QSpinBox::up-arrow,
QSpinBox::down-arrow,
QTimeEdit::up-arrow,
QTimeEdit::down-arrow {
    width: ${space_1}px;
    height: ${space_1}px;
}

QTreeWidget,
QTableView {
    background-color: $bg_surface;
    alternate-background-color: $bg_surface_alt;
    border: ${border_width}px solid $border_default;
    border-radius: ${radius_input}px;
    padding: ${space_1}px;
    gridline-color: $border_default;
}

QTreeWidget::item,
QTableView::item {
    min-height: ${table_row_height}px;
    padding: ${space_1}px;
}

QTreeWidget::item:hover,
QTableView::item:hover {
    background-color: $bg_surface_alt;
}

QTreeWidget::item:selected,
QTableView::item:selected {
    background-color: $bg_selected;
    color: $text_primary;
}

QHeaderView::section {
    background-color: $bg_surface_alt;
    color: $text_secondary;
    border: none;
    border-bottom: ${border_width}px solid $border_default;
    padding: ${space_1}px ${space_2}px;
    font-weight: $font_weight_medium;
}

QCheckBox {
    spacing: ${space_2}px;
    color: $text_primary;
}

QCheckBox:disabled {
    color: $text_disabled;
}

QCheckBox::indicator {
    width: ${icon_size}px;
    height: ${icon_size}px;
    border: ${border_width}px solid $border_strong;
    border-radius: ${radius_input}px;
    background-color: $bg_surface;
}

QCheckBox::indicator:checked {
    background-color: $primary;
    border-color: $primary;
}

QCheckBox::indicator:hover {
    border-color: $primary;
}

QCheckBox::indicator:focus {
    border: ${focus_ring_width}px solid $focus;
}

QCheckBox::indicator:disabled {
    background-color: $bg_surface_alt;
    border-color: $border_default;
}

QProgressBar {
    background-color: $bg_surface_alt;
    border: ${border_width}px solid $border_default;
    border-radius: ${radius_input}px;
    text-align: center;
    min-height: ${control_height_compact}px;
    color: $text_primary;
}

QProgressBar::chunk {
    background-color: $primary;
    border-radius: ${radius_input}px;
}
"""
)


def build_stylesheet(palette: Palette, metrics: Metrics = tokens.METRICS) -> str:
    """Return the QSS for ``palette`` with every design token substituted."""
    values: dict[str, object] = {}
    values.update(asdict(palette))
    values.update(asdict(metrics))
    values.update(
        font_family=tokens.FONT_FAMILY,
        mono_font_family=tokens.MONO_FONT_FAMILY,
        font_size_body=tokens.FONT_SIZE_BODY,
        font_size_small=tokens.FONT_SIZE_SMALL,
        font_size_micro=tokens.FONT_SIZE_MICRO,
        font_size_label=tokens.FONT_SIZE_LABEL,
        font_size_section=tokens.FONT_SIZE_SECTION,
        font_size_page=tokens.FONT_SIZE_PAGE,
        font_size_kpi=tokens.FONT_SIZE_KPI,
        font_size_wizard_title=tokens.FONT_SIZE_WIZARD_TITLE,
        font_weight_regular=tokens.FONT_WEIGHT_REGULAR,
        font_weight_medium=tokens.FONT_WEIGHT_MEDIUM,
        font_weight_semibold=tokens.FONT_WEIGHT_SEMIBOLD,
    )
    return _QSS_TEMPLATE.substitute(values)


__all__ = ["build_stylesheet"]
