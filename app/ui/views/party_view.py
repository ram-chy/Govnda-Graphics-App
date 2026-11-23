"""Customer/Supplier master view."""

from __future__ import annotations

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

from app.domain.party import Party
from app.ui.viewmodels.party_viewmodel import PartySnapshot, PartyViewModel


class PartyView(QWidget):
    def __init__(self, viewmodel: PartyViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel
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
        self.new_btn.clicked.connect(self._vm.new_party)
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
        self.phone = QLineEdit(self)
        self.email = QLineEdit(self)
        self.address = QLineEdit(self)
        self.contact_person = QLineEdit(self)
        self.notes = QPlainTextEdit(self)
        self.notes.setMaximumHeight(90)
        self.active = QCheckBox("Active", self)
        self.active.setChecked(True)

        for label, widget, field in [
            ("Name *", self.name, "name"),
            ("Phone", self.phone, "phone"),
            ("Email", self.email, "email"),
            ("Address", self.address, "address"),
            ("Contact person", self.contact_person, "contact_person"),
            ("Notes", self.notes, "notes"),
        ]:
            form.addRow(label, widget)
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda v, f=field: self._vm.set_field(f, v))
            else:
                widget.textChanged.connect(
                    lambda f=field: self._vm.set_field(f, self.notes.toPlainText())
                )
        form.addRow("Status", self.active)
        self.active.toggled.connect(lambda v: self._vm.set_field("is_active", v))
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

    def _on_select(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        party_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(party_id, int):
            self._vm.select(party_id)

    def _save(self) -> None:
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
        if snap is None or snap.draft.party_id is None:
            return
        self._vm.set_active(not snap.draft.is_active)

    def _on_status(self, message: str) -> None:
        self.feedback.setText(message)

    def _on_error(self, message: str) -> None:
        self.feedback.setText(message)

    def _render(self, snapshot: object) -> None:
        assert isinstance(snapshot, PartySnapshot)
        self._sync_list(snapshot.parties, snapshot.selected_id)
        d = snapshot.draft
        self._set_line(self.name, d.name)
        self._set_line(self.phone, d.phone)
        self._set_line(self.email, d.email)
        self._set_line(self.address, d.address)
        self._set_line(self.contact_person, d.contact_person)
        if self.notes.toPlainText() != d.notes:
            self.notes.blockSignals(True)
            self.notes.setPlainText(d.notes)
            self.notes.blockSignals(False)
        if self.active.isChecked() != d.is_active:
            self.active.blockSignals(True)
            self.active.setChecked(d.is_active)
            self.active.blockSignals(False)
        self.activate_btn.setText("Deactivate" if d.is_active else "Activate")
        self.activate_btn.setEnabled(d.party_id is not None)
        if snapshot.errors:
            self.feedback.setText("; ".join(snapshot.errors))
        elif snapshot.warnings:
            self.feedback.setText(
                "Possible duplicate: " + "; ".join(w.reason for w in snapshot.warnings)
            )
        elif not snapshot.available:
            self.feedback.setText(snapshot.unavailable_reason)

    def _sync_list(self, parties: tuple[Party, ...], selected_id: int | None) -> None:
        current = self.list.currentItem()
        current_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.list.blockSignals(True)
        self.list.clear()
        for p in parties:
            label = p.name + ("" if p.is_active else " (inactive)")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, p.party_id)
            self.list.addItem(item)
            if p.party_id == selected_id:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if selected_id is None and current_id is not None:
            pass

    @staticmethod
    def _set_line(widget: QLineEdit, value: str) -> None:
        if widget.text() != value:
            widget.blockSignals(True)
            widget.setText(value)
            widget.blockSignals(False)
