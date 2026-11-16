"""Phase 4 Windows Task Scheduler and schedule-settings tests."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from app.core import constants
from app.core.config import AppConfig, ConfigService
from app.core.exceptions import ConfigurationError, SchedulerError
from app.infrastructure.backup.task_scheduler import (
    ScheduledTaskSpec,
    TaskQuery,
    WindowsTaskScheduler,
    build_task_xml,
)
from tests.backup_helpers import create_data_root, save_location


class FakeRunner:
    """Simulate ``schtasks.exe`` without touching the real Task Scheduler."""

    def __init__(self, xml: str = "", *, create_code: int = 0) -> None:
        self.xml = xml
        self.create_code = create_code
        self.commands: list[list[str]] = []
        self.deleted = False

    def __call__(self, command) -> subprocess.CompletedProcess[bytes]:
        values = [str(item) for item in command]
        self.commands.append(values)
        if "/Create" in values:
            return subprocess.CompletedProcess(values, self.create_code, b"", b"rejected")
        if "/Delete" in values:
            self.deleted = True
            return subprocess.CompletedProcess(values, 0, b"", b"")
        if "/XML" in values:
            return subprocess.CompletedProcess(values, 0, self.xml.encode("utf-8"), b"")
        if "/Query" in values:
            return subprocess.CompletedProcess(values, 0, b"", b"")
        return subprocess.CompletedProcess(values, 1, b"", b"unknown command")


def _spec(tmp_path: Path) -> ScheduledTaskSpec:
    return ScheduledTaskSpec(
        name=constants.SCHEDULED_TASK_NAME,
        executable=tmp_path / "python.exe",
        arguments='-m app.tools.backup --scheduled --config "C:\\Data\\config.json"',
        working_directory=tmp_path,
        start_time="22:15",
        description='Daily <backup> & "verify"',
    )


def test_task_xml_contains_daily_trigger_and_safe_defaults(tmp_path: Path) -> None:
    xml = build_task_xml(_spec(tmp_path), now=datetime(2026, 1, 2))

    assert "<URI>\\GobindasBMS\\DailyBackup</URI>" in xml
    assert "<StartBoundary>2026-01-02T22:15:00</StartBoundary>" in xml
    assert "<DaysInterval>1</DaysInterval>" in xml
    assert "<LogonType>InteractiveToken</LogonType>" in xml
    assert "<RunLevel>LeastPrivilege</RunLevel>" in xml
    assert "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>" in xml
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in xml
    assert "<ExecutionTimeLimit>PT1H</ExecutionTimeLimit>" in xml
    assert "Daily &lt;backup&gt; &amp; \"verify\"" in xml
    assert (
        '<Arguments>-m app.tools.backup --scheduled --config '
        '"C:\\Data\\config.json"</Arguments>'
    ) in xml


@pytest.mark.parametrize(
    "values",
    [
        {"name": ""},
        {"executable": Path("relative.exe")},
        {"start_time": "24:00"},
        {"start_time": "7:00"},
        {"days_interval": 0},
    ],
)
def test_task_spec_rejects_invalid_values(tmp_path: Path, values: dict[str, object]) -> None:
    arguments: dict[str, object] = {
        "name": constants.SCHEDULED_TASK_NAME,
        "executable": tmp_path / "app.exe",
        "start_time": "22:00",
    }
    arguments.update(values)

    with pytest.raises(ValueError):
        ScheduledTaskSpec(**arguments)  # type: ignore[arg-type]


def test_register_queries_the_task_and_parses_its_fields(tmp_path: Path) -> None:
    xml = build_task_xml(_spec(tmp_path))
    runner = FakeRunner(xml)
    scheduler = WindowsTaskScheduler(runner=runner, platform="win32")

    result = scheduler.register(_spec(tmp_path))

    assert result.exists is True
    assert result.enabled is True
    assert result.command == str(tmp_path / "python.exe")
    assert result.start_boundary.startswith("20")
    assert result.start_when_available is True
    assert result.multiple_instances == "IgnoreNew"
    assert any("/Create" in command for command in runner.commands)
    assert any("/XML" in command for command in runner.commands)


def test_register_reports_windows_rejection(tmp_path: Path) -> None:
    scheduler = WindowsTaskScheduler(runner=FakeRunner(create_code=1), platform="win32")

    with pytest.raises(SchedulerError) as error:
        scheduler.register(_spec(tmp_path))

    assert "did not register" in error.value.user_message
    assert "rejected" in error.value.user_message


def test_register_on_unsupported_platform_fails_closed(tmp_path: Path) -> None:
    scheduler = WindowsTaskScheduler(runner=FakeRunner(), platform="linux")

    assert scheduler.supported is False
    assert scheduler.exists() is False
    assert scheduler.query().exists is False
    with pytest.raises(SchedulerError):
        scheduler.register(_spec(tmp_path))


def test_query_reports_absent_and_malformed_tasks() -> None:
    absent = WindowsTaskScheduler(
        runner=lambda command: subprocess.CompletedProcess(list(command), 1, b"", b"missing"),
        platform="win32",
    )
    assert absent.query().exists is False

    malformed = WindowsTaskScheduler(
        runner=lambda command: subprocess.CompletedProcess(list(command), 0, b"not xml", b""),
        platform="win32",
    )
    result = malformed.query()
    assert result.exists is True
    assert result.enabled is None


def test_remove_is_idempotent_and_verified() -> None:
    runner = FakeRunner()
    scheduler = WindowsTaskScheduler(runner=runner, platform="win32")

    assert scheduler.remove(ignore_missing=True) is True
    assert runner.deleted is True


def test_default_command_uses_the_running_interpreter(tmp_path: Path, monkeypatch) -> None:
    from app.services.schedule_service import default_backup_command

    config_path = tmp_path / "config.json"
    monkeypatch.delattr(sys, "frozen", raising=False)
    executable, arguments, working = default_backup_command(config_path)

    assert executable == Path(sys.executable)
    assert arguments == f'-m app.tools.backup --scheduled --config "{config_path}"'
    assert working.is_dir()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    executable, arguments, working = default_backup_command(config_path)
    assert executable == Path(sys.executable)
    assert arguments == f'--run-backup --scheduled --config "{config_path}"'
    assert working == executable.parent


class FakeScheduler:
    def __init__(self) -> None:
        self.registered: list[ScheduledTaskSpec] = []
        self.removed: list[str] = []
        self.current: TaskQuery | None = None
        self.fail_register = False

    def register(self, spec: ScheduledTaskSpec) -> TaskQuery:
        if self.fail_register:
            raise SchedulerError("registration failed", user_message="Registration failed.")
        self.registered.append(spec)
        self.current = TaskQuery(name=spec.name, exists=True, enabled=True)
        return self.current

    def remove(self, name: str, *, ignore_missing: bool = True) -> bool:
        self.removed.append(name)
        self.current = None
        return True

    def query(self, name: str) -> TaskQuery:
        if self.current is not None:
            return self.current
        return TaskQuery(name=name, exists=False)


def _config_service(tmp_path: Path) -> tuple[ConfigService, Path, Path, Path]:
    root, database_path = create_data_root(tmp_path)
    config_service = ConfigService(tmp_path / "config" / "config.json")
    save_location(config_service, root, database_path)
    return config_service, root, database_path, config_service.config_path


def test_schedule_service_registers_task_before_saving_settings(tmp_path: Path) -> None:
    from app.services.schedule_service import ScheduleService

    config_service, _root, _database, _path = _config_service(tmp_path)
    scheduler = FakeScheduler()
    service = ScheduleService(
        config_service,
        scheduler=scheduler,  # type: ignore[arg-type]
        command_builder=lambda path: (Path(sys.executable), "--run-backup", tmp_path),
    )

    update = service.update_settings(
        enabled=True,
        time="21:30",
        retention_days=45,
        keep_minimum=7,
    )

    assert update.task_registered is True
    assert scheduler.registered
    saved = config_service.load()
    assert saved.backup_enabled is True
    assert saved.backup_time == "21:30"
    assert saved.backup_retention_days == 45
    assert saved.backup_keep_minimum == 7
    assert "21:30" in update.message


def test_schedule_service_disables_and_removes_the_task(tmp_path: Path) -> None:
    from app.services.schedule_service import ScheduleService

    config_service, _root, _database, _path = _config_service(tmp_path)
    scheduler = FakeScheduler()
    service = ScheduleService(
        config_service,
        scheduler=scheduler,  # type: ignore[arg-type]
        command_builder=lambda path: (Path(sys.executable), "--run-backup", tmp_path),
    )

    update = service.update_settings(
        enabled=False,
        time="22:00",
        retention_days=30,
        keep_minimum=5,
    )

    assert update.task_registered is False
    assert scheduler.removed == [constants.SCHEDULED_TASK_NAME]
    assert config_service.load().backup_enabled is False


def test_schedule_service_does_not_save_when_registration_fails(tmp_path: Path) -> None:
    from app.services.schedule_service import ScheduleService

    config_service, _root, _database, _path = _config_service(tmp_path)
    scheduler = FakeScheduler()
    scheduler.fail_register = True
    service = ScheduleService(
        config_service,
        scheduler=scheduler,  # type: ignore[arg-type]
        command_builder=lambda path: (Path(sys.executable), "--run-backup", tmp_path),
    )

    with pytest.raises(SchedulerError):
        service.update_settings(
            enabled=True,
            time="22:00",
            retention_days=30,
            keep_minimum=5,
        )

    assert config_service.load().backup_enabled is constants.DEFAULT_BACKUP_ENABLED


def test_schedule_service_removes_a_new_task_when_config_save_fails(
    tmp_path: Path,
) -> None:
    from app.services.schedule_service import ScheduleService

    class FailingConfigService(ConfigService):
        def save(self, config: AppConfig) -> None:
            raise ConfigurationError("simulated save failure")

    root, database_path = create_data_root(tmp_path)
    path = tmp_path / "config" / "config.json"
    path.parent.mkdir(parents=True)
    ConfigService(path).save(
        AppConfig(data_root=str(root), database_path=str(database_path))
    )
    config_service = FailingConfigService(path)
    scheduler = FakeScheduler()
    service = ScheduleService(
        config_service,
        scheduler=scheduler,  # type: ignore[arg-type]
        command_builder=lambda _path: (Path(sys.executable), "--run-backup", tmp_path),
    )

    with pytest.raises(ConfigurationError):
        service.update_settings(
            enabled=True,
            time="22:00",
            retention_days=30,
            keep_minimum=5,
        )

    assert scheduler.removed == [constants.SCHEDULED_TASK_NAME]
