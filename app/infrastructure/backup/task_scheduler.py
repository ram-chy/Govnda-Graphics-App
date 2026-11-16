"""Windows Task Scheduler integration for the daily backup runner.

The task is registered through the supported ``schtasks.exe`` interface using a
generated Task Scheduler XML definition. No third-party scheduling package and no
COM dependency is required. The task runs as the currently signed-in user with
``InteractiveToken`` and ``LeastPrivilege``: it does not store a password, but it
also runs only while that user is logged on. That limitation is documented in
``docs/BACKUP_STRATEGY.md``.

Every operation is verified by querying the task after it is created, so a
silently rejected registration is reported as a failure instead of an enabled
schedule.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from app.core import constants
from app.core.exceptions import SchedulerError

logger = logging.getLogger(__name__)

_TASK_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[bytes]]


@dataclass(frozen=True, slots=True)
class ScheduledTaskSpec:
    """Everything needed to register the backup task."""

    name: str
    executable: Path
    arguments: str = ""
    working_directory: Path | None = None
    start_time: str = constants.DEFAULT_BACKUP_TIME
    description: str = constants.SCHEDULED_TASK_DESCRIPTION
    days_interval: int = 1
    start_when_available: bool = True
    execution_time_limit: str = "PT1H"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("scheduled task name must not be empty")
        object.__setattr__(self, "executable", Path(self.executable))
        if not self.executable.is_absolute():
            raise ValueError("scheduled task executable must be an absolute path")
        if self.working_directory is not None:
            object.__setattr__(self, "working_directory", Path(self.working_directory))
            if not self.working_directory.is_absolute():
                raise ValueError("scheduled task working directory must be absolute")
        _parse_time(self.start_time)
        if self.days_interval < 1:
            raise ValueError("scheduled task interval must be at least one day")


@dataclass(frozen=True, slots=True)
class TaskQuery:
    """The fields the application verifies after registration."""

    name: str
    exists: bool
    enabled: bool | None = None
    command: str | None = None
    arguments: str | None = None
    start_boundary: str | None = None
    start_when_available: bool | None = None
    multiple_instances: str | None = None
    raw_xml: str = ""

    @property
    def matches(self) -> bool:
        return self.exists and self.enabled is not False


def _parse_time(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
        raise ValueError("time must be HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("time must be a valid 24-hour clock value")
    return hour, minute


def _default_runner(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - fixed, explicit argument list; no shell
        list(command),
        capture_output=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class WindowsTaskScheduler:
    """Create, query, and remove the application's daily backup task."""

    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        schtasks: str = "schtasks.exe",
        platform: str | None = None,
    ) -> None:
        self._runner = runner or _default_runner
        self._schtasks = schtasks
        self._platform = platform or sys.platform

    @property
    def supported(self) -> bool:
        return self._platform == "win32"

    def exists(self, name: str = constants.SCHEDULED_TASK_NAME) -> bool:
        if not self.supported:
            return False
        result = self._run([self._schtasks, "/Query", "/TN", name])
        return result.returncode == 0

    def query(self, name: str = constants.SCHEDULED_TASK_NAME) -> TaskQuery:
        if not self.supported:
            return TaskQuery(name=name, exists=False)
        result = self._run([self._schtasks, "/Query", "/TN", name, "/XML"])
        if result.returncode != 0:
            return TaskQuery(name=name, exists=False, raw_xml=_decode(result.stdout))
        raw = _decode(result.stdout)
        try:
            return _parse_task_xml(name, raw)
        except ET.ParseError:
            logger.warning("Task Scheduler returned XML that could not be parsed for %s", name)
            return TaskQuery(name=name, exists=True, raw_xml=raw)

    def register(self, spec: ScheduledTaskSpec) -> TaskQuery:
        """Create or replace the task and prove that Windows accepted it."""
        if not self.supported:
            raise SchedulerError(
                "Windows Task Scheduler is not available on this platform",
                user_message=(
                    "Automatic backups can only be scheduled in Windows. The setting was "
                    "not saved as enabled."
                ),
            )

        xml = build_task_xml(spec)
        temp_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=".ggbms-task-", suffix=".xml")
            temp_path = Path(name)
            with os.fdopen(descriptor, "wb") as stream:
                # schtasks accepts a Unicode task definition; UTF-16 matches the
                # format exported by Task Scheduler itself.
                stream.write(xml.encode("utf-16"))
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise SchedulerError(
                f"could not prepare the scheduled task definition: {exc}",
                user_message=(
                    "The automatic backup task could not be prepared. Check that the Windows "
                    "temporary folder is writable and try again."
                ),
            ) from exc

        try:
            result = self._run(
                [self._schtasks, "/Create", "/TN", spec.name, "/XML", str(temp_path), "/F"]
            )
        finally:
            temp_path.unlink(missing_ok=True)

        if result.returncode != 0:
            detail = _decode(result.stderr) or _decode(result.stdout) or "unknown error"
            raise SchedulerError(
                f"Task Scheduler rejected task {spec.name!r}: {detail}",
                user_message=(
                    "Windows did not register the automatic backup task. Automatic backups "
                    f"were not enabled. Windows reported: {detail.strip()}"
                ),
            )

        status = self.query(spec.name)
        if not status.exists:
            raise SchedulerError(
                f"task {spec.name!r} was not found after registration",
                user_message=(
                    "Windows accepted the request but the automatic backup task could not be "
                    "found afterwards. Automatic backups were not enabled."
                ),
            )
        logger.info("Scheduled backup task registered: %s", spec.name)
        return status

    def remove(
        self,
        name: str = constants.SCHEDULED_TASK_NAME,
        *,
        ignore_missing: bool = True,
    ) -> bool:
        """Remove the task. Returns whether a task was removed."""
        if not self.supported:
            return False
        result = self._run([self._schtasks, "/Delete", "/TN", name, "/F"])
        if result.returncode == 0:
            logger.info("Scheduled backup task removed: %s", name)
            return True
        detail = _decode(result.stderr) or _decode(result.stdout)
        if ignore_missing and not self.exists(name):
            return False
        raise SchedulerError(
            f"Task Scheduler could not remove task {name!r}: {detail}",
            user_message=(
                "Windows could not remove the automatic backup task. The task may need to be "
                f"removed manually from Task Scheduler. Windows reported: {detail.strip()}"
            ),
        )

    def _run(self, command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
        try:
            return self._runner(command)
        except OSError as exc:
            raise SchedulerError(
                f"Task Scheduler command could not be started: {exc}",
                user_message=(
                    "The Windows Task Scheduler tool could not be started. Automatic backups "
                    "were not changed."
                ),
            ) from exc


def build_task_xml(spec: ScheduledTaskSpec, *, now: datetime | None = None) -> str:
    """Render a Task Scheduler 1.2 XML definition for one daily trigger."""
    hour, minute = _parse_time(spec.start_time)
    moment = now or datetime.now()
    start_boundary = moment.replace(
        hour=hour, minute=minute, second=0, microsecond=0
    ).strftime("%Y-%m-%dT%H:%M:%S")
    name = spec.name.replace("/", "\\")
    uri = name if name.startswith("\\") else f"\\{name}"
    arguments = f"<Arguments>{escape(spec.arguments)}</Arguments>" if spec.arguments else ""
    working = (
        f"<WorkingDirectory>{escape(str(spec.working_directory))}</WorkingDirectory>"
        if spec.working_directory is not None
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        f'<Task version="1.2" xmlns={quoteattr(_TASK_NS)}>\n'
        "  <RegistrationInfo>\n"
        f"    <Description>{escape(spec.description)}</Description>\n"
        f"    <URI>{escape(uri)}</URI>\n"
        "  </RegistrationInfo>\n"
        "  <Triggers>\n"
        "    <CalendarTrigger>\n"
        f"      <StartBoundary>{start_boundary}</StartBoundary>\n"
        "      <Enabled>true</Enabled>\n"
        "      <ScheduleByDay>\n"
        f"        <DaysInterval>{spec.days_interval}</DaysInterval>\n"
        "      </ScheduleByDay>\n"
        "    </CalendarTrigger>\n"
        "  </Triggers>\n"
        "  <Principals>\n"
        '    <Principal id="Author">\n'
        "      <LogonType>InteractiveToken</LogonType>\n"
        "      <RunLevel>LeastPrivilege</RunLevel>\n"
        "    </Principal>\n"
        "  </Principals>\n"
        "  <Settings>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <AllowHardTerminate>true</AllowHardTerminate>\n"
        f"    <StartWhenAvailable>{str(spec.start_when_available).lower()}</StartWhenAvailable>\n"
        "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n"
        "    <IdleSettings>\n"
        "      <StopOnIdleEnd>false</StopOnIdleEnd>\n"
        "      <RestartOnIdle>false</RestartOnIdle>\n"
        "    </IdleSettings>\n"
        "    <AllowStartOnDemand>true</AllowStartOnDemand>\n"
        "    <Enabled>true</Enabled>\n"
        "    <Hidden>false</Hidden>\n"
        "    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n"
        "    <WakeToRun>false</WakeToRun>\n"
        f"    <ExecutionTimeLimit>{escape(spec.execution_time_limit)}</ExecutionTimeLimit>\n"
        "    <Priority>7</Priority>\n"
        "  </Settings>\n"
        '  <Actions Context="Author">\n'
        "    <Exec>\n"
        f"      <Command>{escape(str(spec.executable))}</Command>\n"
        f"      {arguments}\n"
        f"      {working}\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )


def _parse_task_xml(name: str, raw: str) -> TaskQuery:
    root = ET.fromstring(raw)  # noqa: S314 - trusted local schtasks output
    namespace = {"t": _TASK_NS}

    def text(path: str) -> str | None:
        node = root.find(path, namespace)
        return node.text.strip() if node is not None and node.text else None

    def boolean(path: str) -> bool | None:
        value = text(path)
        if value is None:
            return None
        return value.lower() == "true"

    return TaskQuery(
        name=name,
        exists=True,
        enabled=boolean("t:Settings/t:Enabled"),
        command=text("t:Actions/t:Exec/t:Command"),
        arguments=text("t:Actions/t:Exec/t:Arguments"),
        start_boundary=text("t:Triggers/t:CalendarTrigger/t:StartBoundary"),
        start_when_available=boolean("t:Settings/t:StartWhenAvailable"),
        multiple_instances=text("t:Settings/t:MultipleInstancesPolicy"),
        raw_xml=raw,
    )


def _decode(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    for encoding in ("utf-8", "utf-16", "mbcs"):
        try:
            return value.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return value.decode("utf-8", errors="replace")


__all__ = [
    "ScheduledTaskSpec",
    "TaskQuery",
    "WindowsTaskScheduler",
    "build_task_xml",
]
