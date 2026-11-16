"""Cross-process operation lock for backup, restore, relocation, and upgrade.

The lock is an exclusively created file in ``Backups\\.backup.lock`` containing
the owning process ID, process name, start time, and operation. It is not an
in-memory flag: the GUI, the scheduled runner, and maintenance tools all see the
same file.

A stale lock is reclaimed only after the recorded process has been proven dead.
Age alone is never sufficient. A short-lived reclaim guard file serialises the
recovery so two waiting processes cannot both steal a newly created lock.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import platform
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core import constants
from app.core.exceptions import OperationLockedError

logger = logging.getLogger(__name__)

_STILL_ACTIVE = 259
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


@dataclass(frozen=True, slots=True)
class LockOwner:
    """Diagnostic identity of the process holding an operation lock."""

    token: str
    pid: int
    process_name: str
    operation: str
    created_at_utc: datetime
    hostname: str = ""
    app_version: str = constants.APP_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "pid": self.pid,
            "process_name": self.process_name,
            "operation": self.operation,
            "created_at_utc": self.created_at_utc.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "hostname": self.hostname,
            "app_version": self.app_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LockOwner:
        token = data.get("token")
        pid = data.get("pid")
        operation = data.get("operation")
        created = data.get("created_at_utc")
        if not isinstance(token, str) or not token:
            raise ValueError("lock token missing")
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            raise ValueError("lock pid invalid")
        if not isinstance(operation, str) or not operation:
            raise ValueError("lock operation missing")
        if not isinstance(created, str):
            raise ValueError("lock timestamp missing")
        text = created[:-1] + "+00:00" if created.endswith("Z") else created
        moment = datetime.fromisoformat(text)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return cls(
            token=token,
            pid=pid,
            process_name=str(data.get("process_name") or ""),
            operation=operation,
            created_at_utc=moment,
            hostname=str(data.get("hostname") or ""),
            app_version=str(data.get("app_version") or ""),
        )

    def describe(self) -> str:
        age = datetime.now(UTC) - self.created_at_utc
        return (
            f"{self.operation} by {self.process_name or 'unknown process'} "
            f"(PID {self.pid}) started {int(age.total_seconds())} seconds ago"
        )


def process_is_alive(pid: int) -> bool:
    """Return whether ``pid`` still identifies a running process.

    On Windows ``OpenProcess`` plus ``GetExitCodeProcess`` distinguishes a live
    process from a recycled or exited PID. Access denied means the process exists
    but belongs to another user, so it is treated as alive.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform == "win32":
        return _windows_process_is_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _windows_process_is_alive(pid: int) -> bool:
    import ctypes
    import ctypes.wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    kernel32.GetExitCodeProcess.restype = ctypes.wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL

    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        # ERROR_ACCESS_DENIED: the process exists. ERROR_INVALID_PARAMETER: gone.
        return error == 5
    try:
        exit_code = ctypes.wintypes.DWORD(0)
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True
        return exit_code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


class OperationLock:
    """Exclusive file lock for one protected operation."""

    def __init__(
        self,
        path: Path,
        *,
        operation: str,
        process_alive: Callable[[int], bool] = process_is_alive,
        clock: Callable[[], datetime] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._path = Path(path)
        self._operation = operation
        self._process_alive = process_alive
        self._clock = clock or (lambda: datetime.now(UTC))
        self._token_factory = token_factory or (lambda: uuid.uuid4().hex)
        self._owner: LockOwner | None = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def acquired(self) -> bool:
        return self._owner is not None

    @property
    def owner(self) -> LockOwner | None:
        return self._owner

    def acquire(self) -> OperationLock:
        """Acquire the lock or raise :class:`OperationLockedError`.

        A stale lock is reclaimed at most once per call. An unreadable lock file
        is treated as held: corruption is never a reason to break exclusivity.
        """
        if self._owner is not None:
            return self
        self._path.parent.mkdir(parents=True, exist_ok=True)

        for _attempt in range(2):
            owner = self._new_owner()
            try:
                descriptor = os.open(
                    str(self._path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                existing = self._read_owner()
                if existing is None:
                    raise OperationLockedError(
                        f"operation lock exists but is unreadable: {self._path}",
                        user_message=(
                            "Another backup, restore, or database move appears to be running. "
                            "Close other application windows and try again."
                        ),
                    ) from None
                if self._process_alive(existing.pid):
                    raise OperationLockedError(
                        f"operation lock is held: {existing.describe()}",
                        owner=existing,
                        user_message=(
                            f"Another operation is already running ({existing.describe()}). "
                            "Wait for it to finish and try again."
                        ),
                    ) from None
                logger.warning("Reclaiming stale operation lock: %s", existing.describe())
                self._reclaim(existing)
                continue

            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump(owner.to_dict(), stream, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError:
                self._path.unlink(missing_ok=True)
                raise
            self._owner = owner
            logger.info("Operation lock acquired: %s", owner.describe())
            return self

        raise OperationLockedError(
            f"operation lock could not be acquired: {self._path}",
            user_message="Another operation is already running. Try again when it has finished.",
        )

    def release(self) -> None:
        """Release the lock only when this instance still owns it."""
        if self._owner is None:
            return
        current = self._read_owner()
        if current is not None and current.token != self._owner.token:
            logger.warning(
                "Operation lock ownership changed; not deleting another process's lock: %s",
                self._path,
            )
            self._owner = None
            return
        try:
            self._path.unlink(missing_ok=True)
            logger.info("Operation lock released: %s", self._owner.describe())
        except OSError:
            logger.warning("Operation lock could not be removed: %s", self._path, exc_info=True)
        finally:
            self._owner = None

    def __enter__(self) -> OperationLock:
        return self.acquire()

    def __exit__(self, *exc_info: object) -> None:
        self.release()

    def _new_owner(self) -> LockOwner:
        return LockOwner(
            token=self._token_factory(),
            pid=os.getpid(),
            process_name=Path(sys.executable).name if sys.executable else "",
            operation=self._operation,
            created_at_utc=self._clock(),
            hostname=platform.node(),
        )

    def _read_owner(self) -> LockOwner | None:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        try:
            return LockOwner.from_dict(data)
        except (TypeError, ValueError):
            return None

    def _reclaim(self, stale: LockOwner) -> None:
        """Remove a proven-dead owner under a serialising guard file."""
        guard = self._path.with_name(f"{self._path.name}{constants.LOCK_RECLAIM_SUFFIX}")
        guard_owner = self._try_create_guard(guard)
        if guard_owner is None:
            # Another process is recovering the same lock. Treat it as active.
            current = self._read_owner()
            if current is None:
                return
            raise OperationLockedError(
                f"another process is reclaiming the operation lock: {current.describe()}",
                owner=current,
                user_message="Another operation is starting. Try again in a moment.",
            )

        try:
            current = self._read_owner()
            if current is None:
                return
            if current.token != stale.token:
                raise OperationLockedError(
                    f"operation lock changed while recovering: {current.describe()}",
                    owner=current,
                    user_message="Another operation started while the lock was being recovered.",
                )
            if self._process_alive(current.pid):
                raise OperationLockedError(
                    f"operation lock owner is alive: {current.describe()}",
                    owner=current,
                    user_message="Another operation is already running.",
                )
            quarantine = self._path.with_name(
                f".{self._path.name}.stale.{uuid.uuid4().hex[:8]}"
            )
            try:
                os.replace(self._path, quarantine)
            except FileNotFoundError:
                return
            try:
                quarantine.unlink(missing_ok=True)
            except OSError:
                logger.warning("Stale lock quarantine could not be deleted: %s", quarantine)
        finally:
            self._release_guard(guard, guard_owner)

    def _try_create_guard(self, guard: Path) -> LockOwner | None:
        owner = LockOwner(
            token=self._token_factory(),
            pid=os.getpid(),
            process_name=Path(sys.executable).name if sys.executable else "",
            operation=f"{self._operation}:reclaim",
            created_at_utc=self._clock(),
            hostname=platform.node(),
        )
        try:
            descriptor = os.open(str(guard), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            existing = self._read_owner_at(guard)
            if existing is not None and not self._process_alive(existing.pid):
                logger.warning("Removing stale reclaim guard: %s", existing.describe())
                with contextlib.suppress(OSError):
                    guard.unlink()
            return None
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(owner.to_dict(), stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            guard.unlink(missing_ok=True)
            return None
        return owner

    def _release_guard(self, guard: Path, owner: LockOwner) -> None:
        current = self._read_owner_at(guard)
        if current is None or current.token != owner.token:
            return
        try:
            guard.unlink(missing_ok=True)
        except OSError:
            logger.warning("Reclaim guard could not be removed: %s", guard, exc_info=True)

    @staticmethod
    def _read_owner_at(path: Path) -> LockOwner | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        try:
            return LockOwner.from_dict(data)
        except (TypeError, ValueError):
            return None


__all__ = ["LockOwner", "OperationLock", "process_is_alive"]
