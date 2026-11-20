"""Settings page for viewing and editing the business profile."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.domain.business_profile import (
    FIELD_LABELS,
    MANDATORY_TEXT_FIELDS,
    OPTIONAL_FIELDS,
    PROFILE_FIELDS,
    ProfileStatus,
)
from app.ui.components.cards import SectionCard
from app.ui.components.controls import make_button
from app.ui.components.feedback import EmptyState, StatusBadge, apply_status, show_toast
from app.ui.themes.tokens import METRICS
from app.ui.viewmodels.business_profile_viewmodel import (
    BusinessProfileSnapshot,
    BusinessProfileViewModel,
)

_FIELD_ORDER = (*MANDATORY_TEXT_FIELDS, *OPTIONAL_FIELDS)


class BusinessProfileView(QWidget):
    """Presentation-only form driven by :class:`BusinessProfileViewModel`."""

    def __init__(self, viewmodel: BusinessProfileViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentArea")
        self._viewmodel = viewmodel
        self._edits: dict[str, QLineEdit] = {}
        self._errors: dict[str, QLabel] = {}
        self._history_versions: tuple[int, ...] = ()
        self._build_ui()
        self._connect_signals()
        self._viewmodel.refresh()

    @property
    def viewmodel(self) -> BusinessProfileViewModel:
        return self._viewmodel

    @property
    def status_badge(self) -> StatusBadge:
        return self._status

    @property
    def empty_state(self) -> EmptyState:
        return self._empty

    @property
    def save_button(self):
        return self._save_button

    @property
    def reset_button(self):
        return self._reset_button

    @property
    def logo_button(self):
        return self._logo_button

    @property
    def logo_preview_label(self) -> QLabel:
        return self._logo_preview

    @property
    def history_list(self) -> QListWidget:
        return self._history_list

    def field_edit(self, field: str) -> QLineEdit:
        return self._edits[field]

    def error_label(self, field: str) -> QLabel:
        return self._errors[field]

    def set_logo_path(self, path: str | Path) -> None:
        self._viewmodel.choose_logo(path)

    def refresh(self) -> None:
        self._viewmodel.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget(scroll)
        content.setObjectName("BusinessProfileContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_4)

        title = QLabel("Business profile", content)
        title.setObjectName("PageTitle")
        title.setAccessibleName("Business profile")
        layout.addWidget(title)

        note = QLabel(
            "Complete every required field and choose a logo before saving. "
            "Historical versions are retained; no audit screen is provided.",
            content,
        )
        note.setObjectName("MetaLabel")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._status = StatusBadge("Reading business profile...", content)
        layout.addWidget(self._status)

        self._empty = EmptyState(
            "No business profile yet",
            "Complete the required fields and choose a logo to create the profile.",
            content,
        )
        self._empty.setVisible(False)
        layout.addWidget(self._empty)

        form = SectionCard("Business identity", content)
        for field in _FIELD_ORDER:
            self._add_field(form, field)
        layout.addWidget(form)

        brand = SectionCard("Business logo", content)
        self._logo_preview = QLabel("No logo selected", brand)
        self._logo_preview.setObjectName("MetaLabel")
        self._logo_preview.setAccessibleName("Business logo preview")
        self._logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_preview.setMinimumHeight(120)
        brand.content_layout.addWidget(self._logo_preview)
        self._logo_button = make_button(
            "Choose logo...",
            brand,
            variant="secondary",
            accessible_name="Choose a PNG or JPG business logo",
            tooltip="PNG or JPG/JPEG, up to 5 MB",
        )
        brand.content_layout.addWidget(self._logo_button)
        self._errors["logo"] = QLabel("", brand)
        self._errors["logo"].setObjectName("MetaLabel")
        self._errors["logo"].setWordWrap(True)
        self._errors["logo"].setVisible(False)
        brand.content_layout.addWidget(self._errors["logo"])
        layout.addWidget(brand)

        history = SectionCard("Profile history", content)
        self._history_list = QListWidget(history)
        self._history_list.setAccessibleName("Saved business profile versions")
        self._history_list.setMinimumHeight(120)
        history.content_layout.addWidget(self._history_list)
        layout.addWidget(history)

        actions = QHBoxLayout()
        actions.setSpacing(METRICS.space_2)
        self._save_button = make_button(
            "Save profile", content, accessible_name="Save the business profile"
        )
        self._save_button.setToolTip("Validate and save the business profile")
        actions.addWidget(self._save_button)
        self._reset_button = make_button(
            "Discard changes",
            content,
            variant="secondary",
            accessible_name="Discard unsaved business profile changes",
        )
        actions.addWidget(self._reset_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _add_field(self, card: SectionCard, field: str) -> None:
        required = " *" if field in MANDATORY_TEXT_FIELDS else ""
        label = QLabel(f"{FIELD_LABELS[field]}{required}", card)
        label.setObjectName("FieldLabel")
        edit = QLineEdit(card)
        edit.setAccessibleName(FIELD_LABELS[field])
        edit.setMinimumHeight(METRICS.control_height)
        edit.setPlaceholderText(f"Enter {FIELD_LABELS[field].lower()}")
        error = QLabel("", card)
        error.setObjectName("MetaLabel")
        error.setWordWrap(True)
        error.setVisible(False)
        card.content_layout.addWidget(label)
        card.content_layout.addWidget(edit)
        card.content_layout.addWidget(error)
        self._edits[field] = edit
        self._errors[field] = error

    def _connect_signals(self) -> None:
        for field, edit in self._edits.items():
            edit.textChanged.connect(lambda value, name=field: self._on_field_changed(name, value))
        self._logo_button.clicked.connect(self._on_choose_logo)
        self._history_list.itemClicked.connect(self._on_history_clicked)
        self._save_button.clicked.connect(self._viewmodel.save)
        self._reset_button.clicked.connect(self._viewmodel.reset)
        self._viewmodel.snapshot_changed.connect(self._render_snapshot)
        self._viewmodel.status_message.connect(self._show_status)
        self._viewmodel.save_succeeded.connect(self._on_success)
        self._viewmodel.save_failed.connect(self._on_failure)

    def _on_field_changed(self, field: str, value: str) -> None:
        self._viewmodel.set_field(field, value)

    def _on_choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose business logo",
            "",
            "Image files (*.png *.jpg *.jpeg)",
        )
        if path:
            self._viewmodel.choose_logo(path)

    def _on_history_clicked(self, item: QListWidgetItem) -> None:
        version = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(version, int):
            self._viewmodel.select_version(version)

    def _render_snapshot(self, value: object) -> None:
        assert isinstance(value, BusinessProfileSnapshot)
        snapshot = value
        self._set_form_enabled(snapshot.available)
        if not snapshot.available:
            self._status.set_status(snapshot.unavailable_reason, "warning")
        else:
            tone = {
                ProfileStatus.EMPTY: "info",
                ProfileStatus.INCOMPLETE: "warning",
                ProfileStatus.COMPLETE: "pass",
            }[snapshot.completion.status]
            self._status.set_status(snapshot.completion.label, tone)
        self._empty.setVisible(not snapshot.available or snapshot.profile is None)
        if snapshot.unavailable_reason:
            self._empty.detail_label.setText(snapshot.unavailable_reason)
        elif snapshot.profile is None:
            self._empty.detail_label.setText(
                "Complete the required fields and choose a logo to create the profile."
            )
        for field in PROFILE_FIELDS:
            edit = self._edits[field]
            if edit.text() != getattr(snapshot.draft, field):
                edit.setText(getattr(snapshot.draft, field))
        for field, error in self._errors.items():
            message = snapshot.field_errors.get(field, "")
            if message:
                error.setText(message)
                apply_status(error, "error")
                error.setVisible(True)
            else:
                error.clear()
                error.setVisible(False)
        self._render_logo(snapshot)
        self._render_history(snapshot)
        self._reset_button.setEnabled(snapshot.available and snapshot.is_dirty)

    def _render_logo(self, snapshot: BusinessProfileSnapshot) -> None:
        path = snapshot.logo_preview_path
        if path is None or not Path(path).is_file():
            self._logo_preview.setText("No logo selected")
            self._logo_preview.setPixmap(QPixmap())
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._logo_preview.setText(path.name)
            return
        scaled = pixmap.scaled(
            180,
            110,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._logo_preview.setPixmap(scaled)
        self._logo_preview.setText("")

    def _render_history(self, snapshot: BusinessProfileSnapshot) -> None:
        versions = tuple(version.version_number for version in snapshot.versions)
        if versions != self._history_versions:
            self._history_versions = versions
            self._history_list.blockSignals(True)
            self._history_list.clear()
            for version in snapshot.versions:
                item = QListWidgetItem(
                    f"Version {version.version_number} - {version.business_name} "
                    f"({version.created_at})"
                )
                item.setData(Qt.ItemDataRole.UserRole, version.version_number)
                self._history_list.addItem(item)
            self._history_list.blockSignals(False)
        if snapshot.selected_version is None:
            self._history_list.setCurrentRow(-1)
            return
        for index in range(self._history_list.count()):
            item = self._history_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == snapshot.selected_version:
                self._history_list.setCurrentItem(item)
                return

    def _set_form_enabled(self, enabled: bool) -> None:
        for edit in self._edits.values():
            edit.setEnabled(enabled)
        self._logo_button.setEnabled(enabled)
        self._save_button.setEnabled(enabled)
        self._history_list.setEnabled(enabled)

    def _show_status(self, message: str) -> None:
        if message:
            self._status.set_status(message, "info")

    def _on_success(self, message: str) -> None:
        show_toast(self, message, tone="pass")

    def _on_failure(self, message: str) -> None:
        self._status.set_status(message, "error")


__all__ = ["BusinessProfileView"]
