"""Native first-launch setup wizard.

The wizard is pure presentation: all validation, scaffolding, database creation,
and configuration persistence lives in :class:`app.services.setup_service.SetupService`.
Long work runs on a worker thread so the window remains responsive.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QScrollArea,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core import constants
from app.core.config import AppConfig
from app.core.exceptions import AppError
from app.core.logging_config import new_correlation_id
from app.services.setup_service import SetupPersistenceError, SetupResult, SetupService
from app.ui.components.controls import make_button, set_dialog_size
from app.ui.themes.tokens import METRICS
from app.ui.viewmodels.setup_viewmodel import SetupSummary, SetupViewModel

logger = logging.getLogger(__name__)

PAGE_WELCOME = 0
PAGE_LOCATION = 1
PAGE_VALIDATION = 2
PAGE_REVIEW = 3
PAGE_CONFIRM = 4
PAGE_PROGRESS = 5
PAGE_COMPLETION = 6
PAGE_COUNT = 7


class SetupWorker(QObject):
    """Run one setup operation off the GUI thread."""

    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    persistence_failed = Signal(object, str)
    finished = Signal()

    def __init__(
        self,
        service: SetupService,
        data_root: Path,
        base_config: AppConfig,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._data_root = data_root
        self._base_config = base_config

    @Slot()
    def run(self) -> None:
        try:
            result = self._service.initialize(
                self._data_root,
                base_config=self._base_config,
                progress=self.progress.emit,
            )
        except SetupPersistenceError as exc:
            self.persistence_failed.emit(exc.result, exc.user_message)
        except AppError as exc:
            self.failed.emit(exc.user_message)
        except Exception as exc:  # noqa: BLE001 - worker boundary
            correlation_id = new_correlation_id()
            logger.critical(
                "Unexpected setup failure [%s]: %s",
                correlation_id,
                exc,
                exc_info=True,
                extra={"correlation_id": correlation_id},
            )
            self.failed.emit(
                "Setup failed unexpectedly. No existing file was overwritten. "
                f"Reference {correlation_id}; see the application log for details."
            )
        else:
            self.succeeded.emit(result)
        finally:
            self.finished.emit()


class SetupWizard(QDialog):
    """Seven-step wizard for choosing and initializing the business data root."""

    def __init__(
        self,
        service: SetupService,
        base_config: AppConfig,
        *,
        initial_path: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SetupWizard")
        self.setWindowTitle(f"Set up {constants.APP_SHORT_NAME}")
        self.setModal(True)
        set_dialog_size(
            self,
            METRICS.wizard_width,
            METRICS.wizard_height,
            minimum_width=METRICS.wizard_minimum_width,
            minimum_height=METRICS.wizard_minimum_height,
        )

        self._viewmodel = SetupViewModel(service, base_config)
        self._setup_result: SetupResult | None = None
        self._pending_result: SetupResult | None = None
        self._handed_off = False
        self._busy = False
        self._thread: QThread | None = None
        self._worker: SetupWorker | None = None

        self._build_ui()
        if initial_path:
            self._path_edit.setText(initial_path)
        self._set_page(PAGE_WELCOME)

    # ------------------------------------------------------------------ public

    def take_result(self) -> SetupResult | None:
        """Hand ownership of the verified setup result to the caller."""
        result = self._setup_result
        self._setup_result = None
        self._handed_off = True
        return result

    @property
    def current_page(self) -> int:
        return self._stack.currentIndex()

    @property
    def is_busy(self) -> bool:
        return self._busy

    # ---------------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("WizardPages")
        self._stack.addWidget(self._build_welcome_page())
        self._stack.addWidget(self._build_location_page())
        self._stack.addWidget(self._build_validation_page())
        self._stack.addWidget(self._build_review_page())
        self._stack.addWidget(self._build_confirm_page())
        self._stack.addWidget(self._build_progress_page())
        self._stack.addWidget(self._build_completion_page())
        self._stack.currentChanged.connect(lambda _index: self._update_footer())
        layout.addWidget(self._stack, 1)

        layout.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        header = QFrame(self)
        header.setObjectName("WizardHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.space_4,
            METRICS.content_margin_horizontal,
            METRICS.space_4,
        )
        row.setSpacing(METRICS.space_4)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("Business data setup", header)
        title.setObjectName("WizardTitle")
        subtitle = QLabel(
            "Choose where this computer keeps the Gobindas Graphics business database.",
            header,
        )
        subtitle.setObjectName("WizardSubtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        row.addLayout(titles, 1)

        self._step_label = QLabel("Step 1 of 7", header)
        self._step_label.setObjectName("WizardStep")
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._step_label)
        return header

    def _page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(self)
        page.setObjectName("WizardPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
            METRICS.content_margin_horizontal,
            METRICS.content_margin_vertical,
        )
        layout.setSpacing(METRICS.space_4)
        return page, layout

    def _page_title(self, layout: QVBoxLayout, title: str, subtitle: str = "") -> None:
        title_label = QLabel(title, self)
        title_label.setObjectName("PageTitle")
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle, self)
            subtitle_label.setObjectName("WizardSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

    @staticmethod
    def _body(text: str, parent: QWidget) -> QLabel:
        label = QLabel(text, parent)
        label.setObjectName("WizardBody")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _build_welcome_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(
            layout,
            "Welcome",
            "This is the first time the application has started on this computer.",
        )
        layout.addWidget(
            self._body(
                "Business data is stored locally on this computer and works fully offline. "
                "You choose the storage folder, and the application creates the database "
                "and supporting folders there.",
                page,
            )
        )
        layout.addWidget(
            self._body(
                "The live database is never stored inside the application installation "
                "folder, and it is never placed on C: automatically. You can use a fixed "
                "drive or a removable drive that stays connected.",
                page,
            )
        )

        note = QFrame(page)
        note.setProperty("card", True)
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(
            METRICS.space_5, METRICS.space_4, METRICS.space_5, METRICS.space_4
        )
        note_layout.setSpacing(METRICS.space_2)
        note_title = QLabel("What setup will do", note)
        note_title.setObjectName("SectionTitle")
        note_layout.addWidget(note_title)
        for text in (
            "1. Validate the folder, drive, and permissions.",
            "2. Create the Database, Backups, Attachments, and Exports folders.",
            "3. Initialize the SQLite database with the approved schema.",
            "4. Verify the database and save the location in application settings.",
        ):
            note_layout.addWidget(self._body(text, note))
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _build_location_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(
            layout,
            "Choose the business data folder",
            "Select the root folder that will hold the database, backups, attachments, "
            "and exports. Do not choose the application installation folder.",
        )

        path_label = QLabel("Data root folder", page)
        path_label.setObjectName("FieldLabel")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(METRICS.space_2)
        self._path_edit = QLineEdit(page)
        self._path_edit.setPlaceholderText(r"Example: D:\GobindasBusiness")
        self._path_edit.setClearButtonEnabled(True)
        self._path_edit.setAccessibleName("Business data root folder")
        path_label.setBuddy(self._path_edit)
        self._path_edit.textChanged.connect(self._on_path_changed)
        path_row.addWidget(self._path_edit, 1)
        self._browse_button = make_button("Browse...", page, variant="secondary")
        self._browse_button.clicked.connect(self._browse)
        path_row.addWidget(self._browse_button)
        layout.addLayout(path_row)

        hint = QLabel(
            "The folder may already exist or may be new. Its parent folder must exist "
            "and be writable.",
            page,
        )
        hint.setObjectName("MetaLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._location_summary = QLabel("No folder selected yet.", page)
        self._location_summary.setObjectName("WizardPath")
        self._location_summary.setWordWrap(True)
        layout.addWidget(self._location_summary)
        layout.addStretch(1)
        return page

    def _build_validation_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(
            layout,
            "Location check",
            "The application checks the selected folder before creating anything.",
        )
        self._validation_intro = QLabel("", page)
        self._validation_intro.setObjectName("WizardSubtitle")
        self._validation_intro.setWordWrap(True)
        layout.addWidget(self._validation_intro)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        self._validation_container = QWidget(scroll)
        self._validation_layout = QVBoxLayout(self._validation_container)
        self._validation_layout.setContentsMargins(0, 0, 0, 0)
        self._validation_layout.setSpacing(METRICS.space_2)
        self._validation_layout.addStretch(1)
        scroll.setWidget(self._validation_container)
        layout.addWidget(scroll, 1)
        return page

    def _build_review_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(
            layout,
            "Review the folder structure",
            "These folders will be created if they do not already exist. Existing files "
            "and folders are preserved.",
        )
        self._review_tree = QTreeWidget(page)
        self._review_tree.setHeaderHidden(True)
        self._review_tree.setColumnCount(1)
        self._review_tree.setAlternatingRowColors(True)
        self._review_tree.setWordWrap(False)
        self._review_tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._review_tree.setAccessibleName("Planned folders and purposes")
        layout.addWidget(self._review_tree, 1)

        database_caption = QLabel("Database file", page)
        database_caption.setObjectName("FieldLabel")
        layout.addWidget(database_caption)
        self._review_database = QLabel("", page)
        self._review_database.setObjectName("WizardPath")
        self._review_database.setWordWrap(True)
        layout.addWidget(self._review_database)

        self._review_note = self._body("", page)
        layout.addWidget(self._review_note)
        return page

    def _build_confirm_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(
            layout,
            "Confirm setup",
            "Review the location before the database is created.",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(METRICS.space_4)
        grid.setVerticalSpacing(METRICS.space_3)
        self._confirm_root = self._summary_row(grid, 0, "Data root", page)
        self._confirm_database = self._summary_row(grid, 1, "Database file", page)
        self._confirm_drive = self._summary_row(grid, 2, "Drive", page)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self._confirm_warnings = QLabel("", page)
        self._confirm_warnings.setWordWrap(True)
        layout.addWidget(self._confirm_warnings)

        self._confirm_checkbox = QCheckBox("", page)
        self._confirm_checkbox.toggled.connect(lambda _checked: self._update_footer())
        layout.addWidget(self._confirm_checkbox)
        self._confirm_note = self._body(
            "No existing file will be overwritten. If a database already exists at this "
            "location, setup verifies it and refuses to continue unless it is a healthy "
            "Gobindas Graphics database.",
            page,
        )
        layout.addWidget(self._confirm_note)
        layout.addStretch(1)
        return page

    def _build_progress_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(
            layout,
            "Setting up business data",
            "The application is creating folders, initializing the database, and "
            "verifying the result. Keep this window open.",
        )
        self._progress_status = QLabel("Preparing...", page)
        self._progress_status.setWordWrap(True)
        layout.addWidget(self._progress_status)

        self._progress_bar = QProgressBar(page)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)

        self._failure_label = QLabel("", page)
        self._failure_label.setObjectName("WizardError")
        self._failure_label.setWordWrap(True)
        self._failure_label.hide()
        layout.addWidget(self._failure_label)

        self._failure_detail = self._body("", page)
        self._failure_detail.hide()
        layout.addWidget(self._failure_detail)

        failure_buttons = QHBoxLayout()
        failure_buttons.setSpacing(METRICS.space_2)
        self._retry_persist_button = make_button("Retry saving the location", page)
        self._retry_persist_button.clicked.connect(self._retry_persist)
        self._retry_persist_button.hide()
        failure_buttons.addWidget(self._retry_persist_button)
        self._choose_location_button = make_button(
            "Choose another folder", page, variant="secondary"
        )
        self._choose_location_button.clicked.connect(self._return_to_location)
        self._choose_location_button.hide()
        failure_buttons.addWidget(self._choose_location_button)
        failure_buttons.addStretch(1)
        layout.addLayout(failure_buttons)
        layout.addStretch(1)
        return page

    def _build_completion_page(self) -> QWidget:
        page, layout = self._page()
        self._page_title(layout, "Setup complete")
        self._completion_headline = QLabel("The business database is ready.", page)
        self._completion_headline.setObjectName("WizardSuccess")
        self._completion_headline.setWordWrap(True)
        layout.addWidget(self._completion_headline)

        self._completion_body = self._body("", page)
        layout.addWidget(self._completion_body)

        grid = QGridLayout()
        grid.setHorizontalSpacing(METRICS.space_4)
        grid.setVerticalSpacing(METRICS.space_3)
        self._complete_root = self._summary_row(grid, 0, "Data root", page)
        self._complete_database = self._summary_row(grid, 1, "Database file", page)
        self._complete_status = self._summary_row(grid, 2, "Database status", page)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        layout.addWidget(
            self._body(
                "Use Open application to continue. Future launches will open this "
                "database directly without showing setup again.",
                page,
            )
        )
        layout.addStretch(1)
        return page

    def _summary_row(
        self, grid: QGridLayout, row: int, caption: str, parent: QWidget
    ) -> QLabel:
        caption_label = QLabel(caption, parent)
        caption_label.setObjectName("FieldLabel")
        value_label = QLabel("", parent)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(caption_label, row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(value_label, row, 1)
        return value_label

    def _build_footer(self) -> QWidget:
        footer = QFrame(self)
        footer.setObjectName("WizardFooter")
        row = QHBoxLayout(footer)
        row.setContentsMargins(
            METRICS.content_margin_horizontal,
            METRICS.space_4,
            METRICS.content_margin_horizontal,
            METRICS.space_4,
        )
        row.setSpacing(METRICS.space_2)
        row.addStretch(1)

        self._back_button = make_button("Back", footer, variant="secondary")
        self._back_button.clicked.connect(self._go_back)
        row.addWidget(self._back_button)

        self._cancel_button = make_button("Exit setup", footer, variant="secondary")
        self._cancel_button.clicked.connect(self.reject)
        row.addWidget(self._cancel_button)

        self._next_button = make_button("Get started", footer, default=True)
        self._next_button.clicked.connect(self._go_next)
        row.addWidget(self._next_button)
        self.setTabOrder(self._back_button, self._cancel_button)
        self.setTabOrder(self._cancel_button, self._next_button)
        return footer

    # ---------------------------------------------------------------- behaviour

    def _set_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._step_label.setText(f"Step {index + 1} of {PAGE_COUNT}")
        self._update_footer()

    def _update_footer(self) -> None:
        index = self._stack.currentIndex()
        self._back_button.show()
        self._cancel_button.show()
        self._next_button.show()
        self._next_button.setEnabled(True)

        if index == PAGE_WELCOME:
            self._back_button.hide()
            self._next_button.setText("Get started")
            self._cancel_button.setText("Exit setup")
        elif index == PAGE_LOCATION:
            self._next_button.setText("Check location")
            self._next_button.setEnabled(bool(self._path_edit.text().strip()))
            self._cancel_button.setText("Exit setup")
        elif index == PAGE_VALIDATION:
            self._next_button.setText("Review folders")
            self._next_button.setEnabled(self._viewmodel.can_continue)
            self._cancel_button.setText("Exit setup")
        elif index == PAGE_REVIEW:
            self._next_button.setText("Continue")
            self._cancel_button.setText("Exit setup")
        elif index == PAGE_CONFIRM:
            existing = self._summary().existing_database if self._summary() else False
            self._next_button.setText(
                "Connect to existing database" if existing else "Create database"
            )
            self._next_button.setEnabled(self._confirm_checkbox.isChecked())
            self._cancel_button.setText("Cancel setup")
        elif index == PAGE_PROGRESS:
            self._next_button.hide()
            self._back_button.hide()
            self._cancel_button.show()
            self._cancel_button.setText("Setting up..." if self._busy else "Exit setup")
            self._cancel_button.setEnabled(not self._busy)
        elif index == PAGE_COMPLETION:
            self._back_button.hide()
            self._cancel_button.hide()
            self._next_button.setText("Open application")

    def _go_next(self) -> None:
        index = self._stack.currentIndex()
        if index == PAGE_WELCOME:
            self._set_page(PAGE_LOCATION)
            self._path_edit.setFocus()
        elif index == PAGE_LOCATION:
            self._show_validation()
        elif index == PAGE_VALIDATION:
            if self._viewmodel.can_continue:
                self._show_review()
        elif index == PAGE_REVIEW:
            self._show_confirm()
        elif index == PAGE_CONFIRM:
            self._start_initialization()
        elif index == PAGE_COMPLETION:
            self._open_application()

    def _go_back(self) -> None:
        index = self._stack.currentIndex()
        if index == PAGE_LOCATION:
            self._set_page(PAGE_WELCOME)
        elif index == PAGE_VALIDATION:
            self._set_page(PAGE_LOCATION)
        elif index == PAGE_REVIEW:
            self._set_page(PAGE_VALIDATION)
        elif index == PAGE_CONFIRM:
            self._set_page(PAGE_REVIEW)

    def _on_path_changed(self, text: str) -> None:
        self._viewmodel.set_location(text)
        cleaned = text.strip()
        self._location_summary.setText(
            f"Selected folder: {cleaned}" if cleaned else "No folder selected yet."
        )
        self._update_footer()

    def _browse(self) -> None:
        current = self._path_edit.text().strip()
        start = current if current and Path(current).is_dir() else str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self, "Select the business data folder", start
        )
        if chosen:
            self._path_edit.setText(chosen)

    def _show_validation(self) -> None:
        result = self._viewmodel.validate()
        self._render_checks()
        if result.is_valid:
            self._validation_intro.setText(
                "All required checks passed. Review any warnings before continuing."
            )
        else:
            self._validation_intro.setText(
                "The folder cannot be used yet. Correct the problem below and check again."
            )
        self._set_page(PAGE_VALIDATION)

    def _render_checks(self) -> None:
        while self._validation_layout.count():
            item = self._validation_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        result = self._viewmodel.validation
        if result is None:
            self._validation_layout.addStretch(1)
            return
        for check in result.checks:
            row = QFrame(self._validation_container)
            row.setProperty("validationRow", True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(
                METRICS.space_3, METRICS.space_2, METRICS.space_3, METRICS.space_2
            )
            row_layout.setSpacing(METRICS.space_3)

            state = QLabel(check.status.value.upper(), row)
            state.setProperty("checkStatus", check.status.value)
            state.setMinimumWidth(METRICS.space_8 * 2)
            row_layout.addWidget(state, 0, Qt.AlignmentFlag.AlignTop)

            name = QLabel(check.label, row)
            name.setObjectName("FieldLabel")
            name.setMinimumWidth(METRICS.space_8 * 4)
            name.setWordWrap(True)
            row_layout.addWidget(name, 0, Qt.AlignmentFlag.AlignTop)

            message = QLabel(check.message, row)
            message.setWordWrap(True)
            row_layout.addWidget(message, 1)
            self._validation_layout.addWidget(row)
        self._validation_layout.addStretch(1)

    def _summary(self) -> SetupSummary | None:
        return self._viewmodel.summary()

    def _show_review(self) -> None:
        summary = self._summary()
        if summary is None:
            self._set_page(PAGE_LOCATION)
            return
        self._review_tree.clear()
        items: dict[Path, QTreeWidgetItem] = {}
        for path, purpose in self._viewmodel.directory_plan():
            label = str(path) if path == summary.data_root else path.name
            text = f"{label}    —    {purpose}"
            item = QTreeWidgetItem([text])
            item.setToolTip(0, f"{path}\n{purpose}")
            parent_item = items.get(path.parent)
            if parent_item is None:
                self._review_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            items[path] = item

        database_parent = summary.database_path.parent
        database_text = f"{summary.database_path.name}    —    SQLite business database"
        database_item = QTreeWidgetItem([database_text])
        database_item.setToolTip(0, str(summary.database_path))
        if database_parent in items:
            items[database_parent].addChild(database_item)
        else:
            self._review_tree.addTopLevelItem(database_item)
        self._review_tree.expandAll()

        self._review_database.setText(str(summary.database_path))
        if summary.existing_database:
            self._review_note.setText(
                "A database already exists at this location. Setup will verify it and "
                "connect without overwriting the file."
            )
        else:
            self._review_note.setText(
                "No database exists yet. Setup will create it with the approved baseline "
                "schema; existing files and folders are preserved."
            )
        self._set_page(PAGE_REVIEW)

    def _show_confirm(self) -> None:
        summary = self._summary()
        if summary is None:
            self._set_page(PAGE_LOCATION)
            return
        self._confirm_root.setText(str(summary.data_root))
        self._confirm_database.setText(str(summary.database_path))
        self._confirm_drive.setText(summary.drive_description)
        if summary.warnings:
            self._confirm_warnings.setText(
                "\n".join(f"Warning: {item}" for item in summary.warnings)
            )
            self._set_status(self._confirm_warnings, "warning")
        else:
            self._confirm_warnings.setText("No storage warnings for this location.")
            self._set_status(self._confirm_warnings, "pass")

        if summary.existing_database:
            self._confirm_checkbox.setText(
                "I understand setup will verify and connect to the existing database "
                "without overwriting it."
            )
        else:
            self._confirm_checkbox.setText(
                "I have reviewed the location and want to create the business data here."
            )
        self._confirm_checkbox.setChecked(False)
        self._set_page(PAGE_CONFIRM)

    @staticmethod
    def _set_status(label: QLabel, status: str) -> None:
        label.setProperty("checkStatus", status)
        style = label.style()
        style.unpolish(label)
        style.polish(label)

    def _start_initialization(self) -> None:
        if self._busy or self._thread is not None:
            return
        summary = self._summary()
        if summary is None:
            self._set_page(PAGE_LOCATION)
            return

        self._busy = True
        self._pending_result = None
        self._progress_bar.show()
        self._progress_bar.setRange(0, 0)
        self._progress_status.setText("Starting setup...")
        self._failure_label.hide()
        self._failure_detail.hide()
        self._retry_persist_button.hide()
        self._choose_location_button.hide()
        self._set_page(PAGE_PROGRESS)

        thread = QThread(self)
        worker = SetupWorker(
            self._viewmodel.service,
            summary.data_root,
            self._viewmodel.base_config,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.succeeded.connect(self._on_setup_succeeded)
        worker.failed.connect(self._on_setup_failed)
        worker.persistence_failed.connect(self._on_persistence_failed)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)

        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(str)
    def _on_progress(self, message: str) -> None:
        self._progress_status.setText(message)

    @Slot(object)
    def _on_setup_succeeded(self, result: SetupResult) -> None:
        self._busy = False
        self._setup_result = result
        self._pending_result = None
        self._show_completion(result)
        self._set_page(PAGE_COMPLETION)

    @Slot(str)
    def _on_setup_failed(self, message: str) -> None:
        self._busy = False
        self._pending_result = None
        self._show_failure(message, can_retry_persist=False)

    @Slot(object, str)
    def _on_persistence_failed(self, result: SetupResult, message: str) -> None:
        self._busy = False
        self._pending_result = result
        self._show_failure(message, can_retry_persist=True)

    def _show_failure(self, message: str, *, can_retry_persist: bool) -> None:
        self._progress_bar.hide()
        self._progress_status.setText("Setup could not complete.")
        self._failure_label.setText("No existing file was overwritten.")
        self._failure_label.show()
        self._failure_detail.setText(message)
        self._failure_detail.show()
        self._retry_persist_button.setVisible(can_retry_persist)
        self._choose_location_button.setVisible(not can_retry_persist)
        # The footer Next button is hidden on this page, so give keyboard users
        # an explicit default recovery action.
        recovery_button = (
            self._retry_persist_button if can_retry_persist else self._choose_location_button
        )
        recovery_button.setDefault(True)
        recovery_button.setFocus()
        self._set_page(PAGE_PROGRESS)

    def _retry_persist(self) -> None:
        result = self._pending_result
        if result is None:
            return
        try:
            saved = self._viewmodel.service.persist(result)
        except AppError as exc:
            self._failure_detail.setText(exc.user_message)
            return
        self._pending_result = None
        self._setup_result = replace(result, config=saved)
        self._show_completion(self._setup_result)
        self._set_page(PAGE_COMPLETION)

    def _return_to_location(self) -> None:
        self._busy = False
        self._pending_result = None
        self._progress_bar.setRange(0, 0)
        self._failure_label.hide()
        self._failure_detail.hide()
        self._retry_persist_button.hide()
        self._choose_location_button.hide()
        self._next_button.setDefault(True)
        self._set_page(PAGE_LOCATION)

    def _show_completion(self, result: SetupResult) -> None:
        self._completion_headline.setText("The business database is ready.")
        if result.adopted_existing_database:
            self._completion_body.setText(
                "The existing database was verified and connected without being "
                "overwritten or migrated."
            )
        else:
            self._completion_body.setText(
                "The database was created with the approved baseline schema and passed "
                "identity, migration, integrity, and write checks."
            )
        self._complete_root.setText(str(result.data_root))
        self._complete_database.setText(str(result.database_path))
        revision = result.migration.current_revision or "unknown"
        self._complete_status.setText(
            f"Verified healthy · schema {revision} · {result.health.status.value}"
        )

    @Slot()
    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        if not self._busy:
            self._update_footer()

    def _open_application(self) -> None:
        if self._setup_result is None:
            return
        self._handed_off = True
        self.accept()

    # --------------------------------------------------------------- lifecycle

    def reject(self) -> None:
        if self._busy:
            return
        self._release_unclaimed_result()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._busy:
            event.ignore()
            return
        self._release_unclaimed_result()
        super().closeEvent(event)

    def _release_unclaimed_result(self) -> None:
        if self._handed_off:
            return
        if self._setup_result is not None:
            self._setup_result.database.shutdown()
            self._setup_result = None
        if self._pending_result is not None:
            self._pending_result.database.shutdown()
            self._pending_result = None


__all__ = ["SetupWizard"]
