"""Application path handling tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import constants
from app.core.paths import AppPaths, default_paths


def test_default_paths_use_roaming_and_local_appdata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))

    paths = default_paths()

    assert paths.config_dir == tmp_path / "Roaming" / constants.APP_SLUG
    assert paths.log_dir == tmp_path / "Local" / constants.APP_SLUG / "logs"
    assert paths.config_file == paths.config_dir / constants.CONFIG_FILENAME


def test_default_paths_fall_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    paths = default_paths()

    assert paths.config_dir == Path.home() / "AppData" / "Roaming" / constants.APP_SLUG
    assert paths.log_dir == Path.home() / "AppData" / "Local" / constants.APP_SLUG / "logs"


def test_explicit_paths_are_used_as_given(tmp_path: Path) -> None:
    paths = AppPaths(config_dir=tmp_path / "cfg", log_dir=tmp_path / "logs")

    assert paths.config_file == tmp_path / "cfg" / "config.json"
    assert paths.log_file() == tmp_path / "logs" / "app.log"
    assert paths.log_file("backup.log") == tmp_path / "logs" / "backup.log"


@pytest.mark.parametrize("filename", ["", "../escape.log", "sub/dir/app.log", r"..\escape.log"])
def test_log_filename_cannot_escape_log_directory(tmp_path: Path, filename: str) -> None:
    paths = AppPaths(config_dir=tmp_path / "cfg", log_dir=tmp_path / "logs")

    with pytest.raises(ValueError):
        paths.log_file(filename)


def test_ensure_directories_creates_both(tmp_path: Path) -> None:
    paths = AppPaths(config_dir=tmp_path / "cfg", log_dir=tmp_path / "logs")

    paths.ensure_directories()

    assert paths.config_dir.is_dir()
    assert paths.log_dir.is_dir()


def test_paths_require_path_objects(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        AppPaths(config_dir=str(tmp_path), log_dir=tmp_path)  # type: ignore[arg-type]
