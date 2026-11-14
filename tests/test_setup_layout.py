"""Business data root layout tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import constants
from app.infrastructure.filesystem.layout import DataRootLayout


def test_layout_derives_the_complete_approved_structure(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")

    assert layout.database_path == (
        tmp_path / "Business" / "Database" / constants.DATABASE_FILENAME
    )
    assert layout.automatic_backups_dir == tmp_path / "Business" / "Backups" / "Automatic"
    assert layout.manual_backups_dir == tmp_path / "Business" / "Backups" / "Manual"
    assert layout.safety_backups_dir == tmp_path / "Business" / "Backups" / "Safety"
    assert layout.attachments_dir == tmp_path / "Business" / "Attachments"
    assert layout.pdf_exports_dir == tmp_path / "Business" / "Exports" / "PDF"
    assert layout.excel_exports_dir == tmp_path / "Business" / "Exports" / "Excel"


def test_required_directories_are_ordered_parent_first(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")
    directories = layout.required_directories()

    assert directories[0] == layout.root
    assert directories == tuple(dict.fromkeys(directories))
    assert all(directory.is_relative_to(layout.root) for directory in directories)
    assert layout.database_dir in directories
    assert layout.backups_dir in directories
    assert layout.exports_dir in directories


def test_directory_purposes_cover_every_required_directory(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")

    purposes = layout.directory_purposes()

    assert tuple(path for path, _purpose in purposes) == layout.required_directories()
    assert all(purpose for _path, purpose in purposes)


def test_relative_root_is_rejected() -> None:
    with pytest.raises(ValueError, match="absolute"):
        DataRootLayout(Path("Business"))


def test_drive_root_is_rejected() -> None:
    with pytest.raises(ValueError, match="name a directory"):
        DataRootLayout(Path("D:\\"))


def test_database_file_name_must_be_a_plain_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="plain file name"):
        DataRootLayout(tmp_path / "Business", database_file_name="nested/file.db")
