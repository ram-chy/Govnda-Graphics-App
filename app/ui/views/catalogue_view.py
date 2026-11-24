"""Product/Service catalogue view."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.catalogue import CatalogueItem
from app.ui.viewmodels.catalogue_viewmodel import CatalogueSnapshot, CatalogueViewModel


def _price_to_text(minor: int | None) -> str:
    if minor is None:
        return ""
    return f"{Decimal(minor) / Decimal(100):.2f}"


def _parse_price(text: str) -> tuple[int | None, str | None]:
    raw = text.strip()
    if not raw:
        return None, None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None, "Default sale price must be a valid number."
    if value < 0:
        return None, "Default sale price cannot be negative."
    minor = value * Decimal(100)
    if minor != minor.to_integral():
        return None, "Default sale price must have at most 2 decimal places."
    return int(minor), None


class CatalogueView(QWidget):
    def __init__(self, viewmodel: CatalogueViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel
        self._price_error: str | None = None
        self._build()
        self._vm.snapshot_changed.connect(self._render)
        self._vm.status_message.connect(self._on_status)
        self._vm.save_succeeded.connect(self._on_status)
        self._vm.save_failed.connect(self._on_error)
        self._vm.refresh()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        left = QVBoxLayout()
        header = QLabel(f"{self._vm.kind.label}s")
        header.setObjectName("SectionTitle")
        left.addWidget(header)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText(f"Search {self._vm.kind.label.lower()}s...")
        self.search.textChanged.connect(self._vm.set_search)
        left.addWidget(self.search)

        self.include_inactive = QCheckBox("Show inactive", self)
        self.include_inactive.setChecked(True)
        self.include_inactive.toggled.connect(self._vm.set_include_inactive)
        left.addWidget(self.include_inactive)

        self.list = QListWidget(self)
        self.list.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self.list, 1)

        self.new_btn = QPushButton(f"New {self._vm.kind.label.lower()}", self)
        self.new_btn.clicked.connect(self._vm.new_item)
        left.addWidget(self.new_btn)

        left_wrap = QWidget(self)
        left_wrap.setLayout(left)
        left_wrap.setMaximumWidth(360)
        root.addWidget(left_wrap)

        right = QVBoxLayout()
        self.form_title = QLabel(f"{self._vm.kind.label} details")
        self.form_title.setObjectName("SectionTitle")
        right.addWidget(self.form_title)

        form = QFormLayout()
        form.setSpacing(8)
        self.name = QLineEdit(self)
        self.unit = QLineEdit(self)
        self.price = QLineEdit(self)
        self.price.setPlaceholderText("Optional, e.g. 150.00")
        self.description = QPlainTextEdit(self)
        self.description.setMaximumHeight(90)
        self.active = QCheckBox("Active", self)
        self.active.setChecked(True)

        self.name.textChanged.connect(lambda v: self._vm.set_field("name", v))
        self.unit.textChanged.connect(lambda v: self._vm.set_field("unit", v))
        self.price.textChanged.connect(self._on_price_changed)
        self.description.textChanged.connect(
            lambda: self._vm.set_field("description", self.description.toPlainText())
        )
        self.active.toggled.connect(lambda v: self._vm.set_field("is_active", v))

        form.addRow("Name *", self.name)
        form.addRow("Unit", self.unit)
        form.addRow("Default sale price (₹)", self.price)
        form.addRow("Description", self.description)
        form.addRow("Status", self.active)
        right.addLayout(form)

        self.feedback = QLabel("", self)
        self.feedback.setWordWrap(True)
        self.feedback.setObjectName("MetaLabel")
        right.addWidget(self.feedback)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save", self)
        self.save_btn.clicked.connect(self._save)
        self.activate_btn = QPushButton("Deactivate", self)
        self.activate_btn.clicked.connect(self._toggle_active)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.activate_btn)
        buttons.addStretch(1)
        right.addLayout(buttons)
        right.addStretch(1)

        right_wrap = QWidget(self)
        right_wrap.setLayout(right)
        root.addWidget(right_wrap, 1)

    def _on_price_changed(self, value: str) -> None:
        minor, error = _parse_price(value)
        self._price_error = error
        if error is None:
            self._vm.set_field("default_sale_price_minor", minor)
        else:
            self.feedback.setText(error)

    def _on_select(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(item_id, int):
            self._vm.select(item_id)

    def _save(self) -> None:
        minor, error = _parse_price(self.price.text())
        self._price_error = error
        if error is not None:
            self.feedback.setText(error)
            self._on_error(error)
            return
        self._vm.set_field("default_sale_price_minor", minor)

        snap = self._vm.snapshot
        if snap is not None and snap.warnings:
            names = "\n".join(f"- {w.reason}" for w in snap.warnings)
            reply = QMessageBox.question(
                self,
                "Possible duplicate",
                f"{names}\n\nSave anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._vm.save(confirm_duplicates=True)
            return
        self._vm.save(confirm_duplicates=False)

    def _toggle_active(self) -> None:
        snap = self._vm.snapshot
        if snap is None or snap.draft.item_id is None:
            return
        self._vm.set_active(not snap.draft.is_active)

    def _on_status(self, message: str) -> None:
        self.feedback.setText(message)

    def _on_error(self, message: str) -> None:
        self.feedback.setText(message)

    def _render(self, snapshot: object) -> None:
        assert isinstance(snapshot, CatalogueSnapshot)
        self._sync_list(snapshot.items, snapshot.selected_id)
        d = snapshot.draft
        self._set_line(self.name, d.name)
        self._set_line(self.unit, d.unit)
        price_text = _price_to_text(d.default_sale_price_minor)
        if self.price.text() != price_text and self._price_error is None:
            self._set_line(self.price, price_text)
        if self.description.toPlainText() != d.description:
            self.description.blockSignals(True)
            self.description.setPlainText(d.description)
            self.description.blockSignals(False)
        if self.active.isChecked() != d.is_active:
            self.active.blockSignals(True)
            self.active.setChecked(d.is_active)
            self.active.blockSignals(False)
        self.activate_btn.setText("Deactivate" if d.is_active else "Activate")
        self.activate_btn.setEnabled(d.item_id is not None)
        if snapshot.errors:
            self.feedback.setText("; ".join(snapshot.errors))
        elif snapshot.warnings:
            self.feedback.setText(
                "Possible duplicate: " + "; ".join(w.reason for w in snapshot.warnings)
            )
        elif not snapshot.available:
            self.feedback.setText(snapshot.unavailable_reason)

    def _sync_list(self, items: tuple[CatalogueItem, ...], selected_id: int | None) -> None:
        current = self.list.currentItem()
        current_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.list.blockSignals(True)
        self.list.clear()
        for item in items:
            label = item.name + ("" if item.is_active else " (inactive)")
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
            self.list.addItem(list_item)
            if item.item_id == selected_id:
                self.list.setCurrentItem(list_item)
        self.list.blockSignals(False)
        if selected_id is None and current_id is not None:
            pass

    @staticmethod
    def _set_line(widget: QLineEdit, value: str) -> None:
        if widget.text() != value:
            widget.blockSignals(True)
            widget.setText(value)
            widget.blockSignals(False)
