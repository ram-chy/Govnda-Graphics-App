"""Safe creation and cleanup of the business data directory layout."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import SetupError
from app.infrastructure.filesystem.layout import DataRootLayout
from app.infrastructure.filesystem.scaffold import DataRootScaffolder


def test_scaffold_creates_every_required_directory(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")

    result = DataRootScaffolder().create(layout)

    assert all(directory.is_dir() for directory in layout.required_directories())
    assert set(result.created_paths) == set(layout.required_directories())
    assert result.existing_paths == ()


def test_scaffold_preserves_existing_folders_and_files(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")
    layout.backups_dir.mkdir(parents=True)
    existing_file = layout.backups_dir / "manual-backup.zip"
    existing_file.write_text("user data", encoding="utf-8")

    result = DataRootScaffolder().create(layout)

    assert layout.backups_dir in result.existing_paths
    assert existing_file.read_text(encoding="utf-8") == "user data"
    assert (layout.attachments_dir).is_dir()


def test_scaffold_refuses_to_replace_a_file_with_a_directory(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")
    layout.root.mkdir()
    blocker = layout.database_dir
    blocker.write_text("do not delete", encoding="utf-8")

    with pytest.raises(SetupError, match="not a directory"):
        DataRootScaffolder().create(layout)

    assert blocker.read_text(encoding="utf-8") == "do not delete"


def test_partial_failure_removes_only_empty_directories_it_created(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")
    layout.pdf_exports_dir.mkdir(parents=True)
    blocker = layout.pdf_exports_dir / "keep.txt"
    blocker.write_text("user data", encoding="utf-8")
    # A file where the PDF folder exists is already impossible here; instead make
    # the Excel folder a file so creation fails after several directories exist.
    layout.excel_exports_dir.parent.mkdir(parents=True, exist_ok=True)
    layout.excel_exports_dir.write_text("not a directory", encoding="utf-8")

    with pytest.raises(SetupError):
        DataRootScaffolder().create(layout)

    assert blocker.read_text(encoding="utf-8") == "user data"
    assert layout.excel_exports_dir.read_text(encoding="utf-8") == "not a directory"
    # Directories created by this failed attempt and still empty are removed.
    assert not layout.database_dir.exists()
    assert not layout.attachments_dir.exists()


def test_cleanup_does_not_remove_non_empty_created_directories(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")
    scaffolder = DataRootScaffolder()
    result = scaffolder.create(layout)
    keep = layout.attachments_dir / "scan.pdf"
    keep.write_text("attachment", encoding="utf-8")

    removed = scaffolder.cleanup(result)

    assert keep.is_file()
    assert layout.attachments_dir.exists()
    assert layout.attachments_dir not in removed


def test_cleanup_never_removes_pre_existing_directories(tmp_path: Path) -> None:
    layout = DataRootLayout(tmp_path / "Business")
    layout.backups_dir.mkdir(parents=True)
    scaffolder = DataRootScaffolder()
    result = scaffolder.create(layout)

    removed = scaffolder.cleanup(result)

    assert layout.backups_dir.is_dir()
    assert layout.backups_dir not in removed


def test_permission_failure_is_wrapped_as_setup_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = DataRootLayout(tmp_path / "Business")

    def failing_mkdir(self: Path, *_args: object, **_kwargs: object) -> None:
        raise PermissionError("simulated access denied")

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)

    with pytest.raises(SetupError, match="could not create"):
        DataRootScaffolder().create(layout)
