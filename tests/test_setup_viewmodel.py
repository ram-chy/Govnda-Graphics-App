"""Setup view model state and summaries."""

from __future__ import annotations

from pathlib import Path

from app.core.config import AppConfig, ConfigService
from app.infrastructure.filesystem.drives import DriveInfo, DriveType
from app.infrastructure.filesystem.validation import DataLocationValidator
from app.services.setup_service import SetupService
from app.ui.viewmodels.setup_viewmodel import SetupViewModel


def _viewmodel(tmp_path: Path, drive_type: DriveType = DriveType.FIXED) -> SetupViewModel:
    def provider(root: Path) -> DriveInfo:
        return DriveInfo(
            root=Path(root),
            drive_type=drive_type,
            label="Test volume",
            filesystem="NTFS",
            total_bytes=10 * 1024**3,
            free_bytes=10 * 1024**3,
        )

    validator = DataLocationValidator(
        installation_dirs=[],
        protected_dirs=[],
        drive_info_provider=provider,
        write_probe=lambda _path: None,
    )
    service = SetupService(
        ConfigService(tmp_path / "config" / "config.json"), validator=validator
    )
    return SetupViewModel(service, AppConfig())


def test_location_changes_are_published(tmp_path: Path) -> None:
    viewmodel = _viewmodel(tmp_path)
    received: list[str] = []
    viewmodel.location_changed.connect(received.append)

    viewmodel.set_location("  D:/Business  ")
    viewmodel.set_location("  D:/Business  ")

    assert viewmodel.location == "D:/Business"
    assert received == ["D:/Business"]
    assert viewmodel.validation is None
    assert not viewmodel.can_continue


def test_validation_is_published_and_enables_continue(tmp_path: Path) -> None:
    viewmodel = _viewmodel(tmp_path)
    published: list[object] = []
    viewmodel.validation_changed.connect(published.append)
    root = tmp_path / "Business"
    viewmodel.set_location(str(root))

    result = viewmodel.validate()

    assert result.is_valid
    assert viewmodel.can_continue
    assert published == [result]
    assert viewmodel.validation is result


def test_summary_reports_location_drive_and_warnings(tmp_path: Path) -> None:
    viewmodel = _viewmodel(tmp_path, drive_type=DriveType.REMOVABLE)
    viewmodel.set_location(str(tmp_path / "Business"))
    viewmodel.validate()

    summary = viewmodel.summary()

    assert summary is not None
    assert summary.data_root == tmp_path / "Business"
    assert summary.database_path == (
        tmp_path / "Business" / "Database" / "BusinessManagement.db"
    )
    assert "Removable drive" in summary.drive_description
    assert summary.warnings
    assert not summary.existing_database


def test_summary_detects_an_existing_database(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    database_path = root / "Database" / "BusinessManagement.db"
    database_path.parent.mkdir(parents=True)
    database_path.write_bytes(b"existing")
    viewmodel = _viewmodel(tmp_path)
    viewmodel.set_location(str(root))
    viewmodel.validate()

    summary = viewmodel.summary()

    assert summary is not None
    assert summary.existing_database


def test_summary_and_plan_are_empty_before_validation(tmp_path: Path) -> None:
    viewmodel = _viewmodel(tmp_path)
    viewmodel.set_location(str(tmp_path / "Business"))

    assert viewmodel.summary() is None
    assert viewmodel.directory_plan() == ()


def test_directory_plan_lists_every_folder(tmp_path: Path) -> None:
    viewmodel = _viewmodel(tmp_path)
    viewmodel.set_location(str(tmp_path / "Business"))
    viewmodel.validate()

    plan = viewmodel.directory_plan()

    assert plan
    assert plan[0][0] == tmp_path / "Business"
    assert all(path.is_absolute() for path, _purpose in plan)
    assert len(plan) == 10
