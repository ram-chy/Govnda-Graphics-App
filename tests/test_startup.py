"""End-to-end startup test for the real entry point.

The application is started in a subprocess with isolated APPDATA and
LOCALAPPDATA folders and the offscreen Qt platform.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _isolated_env(tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["APPDATA"] = str(tmp_path / "Roaming")
    environment["LOCALAPPDATA"] = str(tmp_path / "Local")
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    # Each test gets its own mutex so a running application (or another test)
    # cannot make startup fail for an unrelated reason.
    environment["GOBINDAS_MUTEX_NAME"] = rf"Local\GGBMS.Test.{uuid.uuid4().hex}"
    return environment


def _run_smoke(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.main", "--smoke-test"],
        cwd=PROJECT_ROOT,
        env=_isolated_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_application_starts_and_exits_cleanly(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    log_file = tmp_path / "Local" / "GobindasBMS" / "logs" / "app.log"
    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "Main window shown" in content
    assert "Smoke test mode: quitting automatically" in content
    assert "Application exiting" in content
    assert "Traceback" not in content
    assert "CRITICAL" not in content
    assert "ERROR" not in content


def test_corrupt_config_does_not_prevent_startup(tmp_path: Path) -> None:
    config_dir = tmp_path / "Roaming" / "GobindasBMS"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text("{ this is not json", encoding="utf-8")

    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    log_file = tmp_path / "Local" / "GobindasBMS" / "logs" / "app.log"
    content = log_file.read_text(encoding="utf-8")
    assert "Configuration file is invalid" in content
    assert "Main window shown" in content
    assert list(config_dir.glob("config.corrupt-*.json"))


def test_startup_creates_no_database_files(tmp_path: Path) -> None:
    result = _run_smoke(tmp_path)

    assert result.returncode == 0, result.stderr
    database_files = [
        path
        for path in tmp_path.rglob("*")
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm"}
    ]
    assert database_files == []
