"""Recovery dialog: safe choices only, and no file-system side effects."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QLabel, QPushButton

from app.ui.dialogs.recovery_dialog import RecoveryAction, RecoveryDialog

MESSAGE = "The drive for the configured database is not available (D:\\)."


def _button(dialog: RecoveryDialog, text: str) -> QPushButton:
    matches = [button for button in dialog.findChildren(QPushButton) if button.text() == text]
    assert len(matches) == 1, [button.text() for button in dialog.findChildren(QPushButton)]
    return matches[0]


def _label_texts(dialog: RecoveryDialog) -> list[str]:
    return [label.text() for label in dialog.findChildren(QLabel)]


def test_dialog_defaults_to_exit_and_shows_saved_locations(
    qapp, tmp_path: Path
) -> None:
    database_path = Path("D:/Business/Database/BusinessManagement.db")
    data_root = Path("D:/Business")
    quarantine = tmp_path / "config.corrupt-20261114-120000.json"
    dialog = RecoveryDialog(
        MESSAGE,
        database_path=database_path,
        data_root=data_root,
        quarantine_path=quarantine,
    )

    try:
        assert dialog.action is RecoveryAction.EXIT
        texts = _label_texts(dialog)
        assert MESSAGE in texts
        assert str(database_path) in texts
        assert str(data_root) in texts
        assert str(quarantine) in texts
        assert any("No replacement database was created" in text for text in texts)
    finally:
        dialog.close()


def test_unconfigured_locations_are_described_without_inventing_paths(
    qapp,
) -> None:
    dialog = RecoveryDialog("Settings are incomplete.")

    try:
        texts = _label_texts(dialog)
        assert texts.count("(not configured)") == 2
        assert "(not moved)" in texts
    finally:
        dialog.close()


def test_retry_accepts_the_dialog(qapp) -> None:
    dialog = RecoveryDialog(MESSAGE)

    try:
        _button(dialog, "Retry").click()

        assert dialog.action is RecoveryAction.RETRY
        assert dialog.result() == QDialog.DialogCode.Accepted
    finally:
        dialog.close()


def test_locate_accepts_the_dialog(qapp) -> None:
    dialog = RecoveryDialog(MESSAGE)

    try:
        _button(dialog, "Locate existing data...").click()

        assert dialog.action is RecoveryAction.LOCATE
        assert dialog.result() == QDialog.DialogCode.Accepted
    finally:
        dialog.close()


def test_new_setup_accepts_the_dialog(qapp) -> None:
    dialog = RecoveryDialog(MESSAGE)

    try:
        _button(dialog, "Start a new setup...").click()

        assert dialog.action is RecoveryAction.NEW_SETUP
        assert dialog.result() == QDialog.DialogCode.Accepted
    finally:
        dialog.close()


def test_exit_rejects_the_dialog(qapp) -> None:
    dialog = RecoveryDialog(MESSAGE)

    try:
        _button(dialog, "Exit").click()

        assert dialog.action is RecoveryAction.EXIT
        assert dialog.result() == QDialog.DialogCode.Rejected
    finally:
        dialog.close()


def test_dialog_never_touches_the_saved_locations(qapp, tmp_path: Path) -> None:
    data_root = tmp_path / "Business"
    database_path = data_root / "Database" / "BusinessManagement.db"
    dialog = RecoveryDialog(MESSAGE, database_path=database_path, data_root=data_root)

    try:
        _button(dialog, "Retry").click()
        _button(dialog, "Locate existing data...").click()
        _button(dialog, "Start a new setup...").click()
        _button(dialog, "Exit").click()

        assert not data_root.exists()
        assert not database_path.exists()
    finally:
        dialog.close()
