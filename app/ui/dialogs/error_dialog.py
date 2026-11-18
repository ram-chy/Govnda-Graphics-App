"""User-facing error dialogs.

Dialogs show what happened, what is safe, and a correlation ID. Technical
details stay in the log file; tracebacks and SQL are never displayed.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget


def show_error_dialog(
    parent: QWidget | None,
    *,
    title: str,
    message: str,
    correlation_id: str,
    log_path: Path,
) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(message)
    box.setInformativeText(
        "No business data was changed. If the problem continues, contact support "
        f"and quote reference {correlation_id}."
    )
    box.setDetailedText(f"Application log:\n{log_path}")
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    # The reference must be selectable and copyable without opening Details.
    box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    copy_button = box.addButton(
        "Copy reference", QMessageBox.ButtonRole.ActionRole
    )
    copy_button.setAccessibleName("Copy the error reference to the clipboard")
    copy_button.clicked.connect(
        lambda: QApplication.clipboard().setText(correlation_id)
    )
    box.exec()


def show_fatal_error(
    parent: QWidget | None,
    correlation_id: str,
    log_path: Path,
    *,
    message: str = "The application encountered an unexpected problem and cannot continue.",
) -> None:
    show_error_dialog(
        parent,
        title="Gobindas Graphics - Unexpected error",
        message=message,
        correlation_id=correlation_id,
        log_path=log_path,
    )


__all__ = ["show_error_dialog", "show_fatal_error"]
