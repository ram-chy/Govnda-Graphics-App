"""Validation policy for the setup wizard."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import constants
from app.infrastructure.filesystem import validation as validation_module
from app.infrastructure.filesystem.drives import DriveInfo, DriveType
from app.infrastructure.filesystem.layout import DataRootLayout
from app.infrastructure.filesystem.validation import (
    CheckStatus,
    DataLocationValidator,
    default_installation_dirs,
    default_protected_dirs,
)


def _fixed_drive(path: Path, free_bytes: int = 10 * 1024**3) -> DriveInfo:
    return DriveInfo(
        root=Path(path.anchor),
        drive_type=DriveType.FIXED,
        label="Data",
        filesystem="NTFS",
        total_bytes=free_bytes,
        free_bytes=free_bytes,
    )


def _validator(
    *,
    drive_type: DriveType = DriveType.FIXED,
    free_bytes: int = 10 * 1024**3,
    installation_dirs: list[Path] | None = None,
    protected_dirs: list[Path] | None = None,
    write_probe=None,
    minimum_free_bytes: int = constants.MINIMUM_FREE_SPACE_BYTES,
) -> DataLocationValidator:
    def provider(root: Path) -> DriveInfo:
        return DriveInfo(
            root=Path(root),
            drive_type=drive_type,
            label="Test volume",
            filesystem="NTFS",
            total_bytes=free_bytes,
            free_bytes=free_bytes,
        )

    return DataLocationValidator(
        installation_dirs=installation_dirs if installation_dirs is not None else [],
        protected_dirs=protected_dirs if protected_dirs is not None else [],
        drive_info_provider=provider,
        write_probe=write_probe or (lambda _path: None),
        minimum_free_bytes=minimum_free_bytes,
    )


def _keys(result) -> set[str]:
    return {check.key for check in result.checks}


def test_valid_existing_fixed_drive_location(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    root.mkdir()

    result = _validator().validate(root)

    assert result.is_valid
    assert result.layout is not None
    assert result.layout.root == root
    assert result.drive is not None
    assert result.drive.drive_type is DriveType.FIXED
    assert {"path", "absolute", "network", "drive_available", "directory", "read", "write"} <= (
        _keys(result)
    )


def test_valid_new_folder_uses_existing_parent(tmp_path: Path) -> None:
    root = tmp_path / "Business"

    result = _validator().validate(root)

    assert result.is_valid
    assert result.layout is not None
    assert not root.exists()
    directory_check = next(check for check in result.checks if check.key == "directory")
    assert directory_check.status is CheckStatus.INFO


def test_empty_and_relative_paths_are_rejected() -> None:
    validator = _validator()

    for value in (None, "", "   ", "relative/folder"):
        result = validator.validate(value)
        assert not result.is_valid, value
        assert result.errors[0].key in {"path", "absolute"}


def test_missing_parent_is_rejected_when_an_ancestor_is_a_file(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker.txt"
    blocker.write_text("not a folder", encoding="utf-8")

    result = _validator().validate(blocker / "Business")

    assert not result.is_valid
    assert result.errors[0].key == "parent"


def test_a_file_is_not_accepted_as_the_data_root(tmp_path: Path) -> None:
    target = tmp_path / "Business"
    target.write_text("file", encoding="utf-8")

    result = _validator().validate(target)

    assert not result.is_valid
    assert result.errors[0].key == "directory"


def test_read_access_failure_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "Business"
    root.mkdir()
    monkeypatch.setattr(validation_module, "_can_read_directory", lambda _path: False)

    result = _validator().validate(root)

    assert not result.is_valid
    assert result.errors[0].key == "read"


def test_unwritable_location_is_rejected_without_touching_files(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    root.mkdir()
    sentinel = root / "keep.txt"
    sentinel.write_text("user data", encoding="utf-8")

    def failing_probe(_path: Path) -> None:
        raise PermissionError("simulated read-only volume")

    result = _validator(write_probe=failing_probe).validate(root)

    assert not result.is_valid
    assert result.errors[0].key == "write"
    assert sentinel.read_text(encoding="utf-8") == "user data"


def test_unc_path_is_rejected(tmp_path: Path) -> None:
    result = _validator().validate(r"\\server\share\GobindasBusiness")

    assert not result.is_valid
    assert result.errors[0].key == "network"


def test_installation_directory_is_rejected(tmp_path: Path) -> None:
    result = _validator(installation_dirs=[tmp_path]).validate(tmp_path / "Business")

    assert not result.is_valid
    assert result.errors[0].key == "installation"


def test_protected_directory_is_rejected(tmp_path: Path) -> None:
    protected = tmp_path / "Windows"
    protected.mkdir()

    result = _validator(protected_dirs=[protected]).validate(protected / "Business")

    assert not result.is_valid
    assert result.errors[0].key == "protected"


def test_drive_root_is_rejected_as_unsuitable(tmp_path: Path) -> None:
    result = _validator().validate(Path(tmp_path.anchor))

    assert not result.is_valid
    assert result.errors[0].key == "layout"


def test_removable_drive_is_allowed_with_a_warning(tmp_path: Path) -> None:
    result = _validator(drive_type=DriveType.REMOVABLE).validate(tmp_path / "Business")

    assert result.is_valid
    assert result.warnings
    assert "Keep this drive connected" in result.warnings[0].message


def test_unknown_drive_type_is_a_warning(tmp_path: Path) -> None:
    result = _validator(drive_type=DriveType.UNKNOWN).validate(tmp_path / "Business")

    assert result.is_valid
    assert result.warnings
    assert "could not be identified" in result.warnings[0].message


@pytest.mark.parametrize("drive_type", [DriveType.NETWORK, DriveType.CDROM])
def test_unsupported_drive_types_are_rejected(tmp_path: Path, drive_type: DriveType) -> None:
    result = _validator(drive_type=drive_type).validate(tmp_path / "Business")

    assert not result.is_valid
    assert result.errors[0].key == "drive_type"


def test_unavailable_drive_is_rejected(tmp_path: Path) -> None:
    def provider(root: Path) -> DriveInfo:
        return DriveInfo(root=Path(root), drive_type=DriveType.UNAVAILABLE)

    validator = DataLocationValidator(
        installation_dirs=[],
        protected_dirs=[],
        drive_info_provider=provider,
        write_probe=lambda _path: None,
    )

    result = validator.validate(tmp_path / "Business")

    assert not result.is_valid
    assert result.errors[0].key == "drive_type"


def test_available_space_is_reported(tmp_path: Path) -> None:
    result = _validator(free_bytes=5 * 1024**3).validate(tmp_path / "Business")

    assert result.is_valid
    space_check = next(check for check in result.checks if check.key == "space")
    assert space_check.status is CheckStatus.PASS
    assert "available on drive" in space_check.message


def test_insufficient_space_is_rejected(tmp_path: Path) -> None:
    result = _validator(free_bytes=constants.MINIMUM_FREE_SPACE_BYTES - 1).validate(
        tmp_path / "Business"
    )

    assert not result.is_valid
    assert result.errors[0].key == "space"


def test_existing_database_is_reported_as_a_warning(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    database_path = DataRootLayout(root).database_path
    database_path.parent.mkdir(parents=True)
    database_path.write_bytes(b"existing")

    result = _validator().validate(root)

    assert result.is_valid
    check = next(check for check in result.checks if check.key == "existing_database")
    assert check.status is CheckStatus.WARNING
    assert database_path.read_bytes() == b"existing"


def test_directory_at_the_database_path_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "Business"
    database_path = DataRootLayout(root).database_path
    database_path.mkdir(parents=True)

    result = _validator().validate(root)

    assert not result.is_valid
    assert result.errors[0].key == "existing_database"


def test_long_path_is_a_warning(tmp_path: Path) -> None:
    root = tmp_path / ("a" * 60) / ("b" * 60) / ("c" * 60) / "Business"

    result = _validator().validate(root)

    assert result.is_valid
    assert any(check.key == "path_length" for check in result.warnings)


def test_default_write_probe_leaves_no_file_behind(tmp_path: Path) -> None:
    validator = DataLocationValidator(
        installation_dirs=[],
        protected_dirs=[],
        drive_info_provider=_fixed_drive,
    )

    result = validator.validate(tmp_path)

    assert result.is_valid
    assert list(tmp_path.glob(".ggbms-setup-probe-*")) == []


def test_default_directory_helpers_return_absolute_paths() -> None:
    assert all(path.is_absolute() for path in default_installation_dirs())
    assert all(path.is_absolute() for path in default_protected_dirs())
