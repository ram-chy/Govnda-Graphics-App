"""Single-instance guard based on a named Windows mutex (ADR-013)."""

from __future__ import annotations

import logging
import sys
import types
from typing import Any

from app.core.constants import MUTEX_NAME

logger = logging.getLogger(__name__)

_ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    """Own a named mutex for the lifetime of the GUI process.

    On non-Windows platforms the guard is a no-op so the code remains testable;
    the shipped application targets Windows only.
    """

    def __init__(self, name: str = MUTEX_NAME) -> None:
        self._name = name
        self._handle: Any | None = None

    @property
    def is_locked(self) -> bool:
        return self._handle is not None

    def acquire(self) -> bool:
        """Return True when this process owns the mutex, False if already running."""
        if sys.platform != "win32":
            logger.debug("Single-instance guard is a no-op on %s", sys.platform)
            return True
        if self._handle is not None:
            return True

        ctypes, wintypes = _load_ctypes()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE

        handle = kernel32.CreateMutexW(None, False, self._name)
        if not handle:
            error_code = ctypes.get_last_error()
            raise OSError(error_code, f"CreateMutexW failed for {self._name}")

        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def release(self) -> None:
        """Release and close the mutex. Safe to call multiple times."""
        if self._handle is None:
            return

        ctypes, wintypes = _load_ctypes()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        kernel32.ReleaseMutex(self._handle)
        kernel32.CloseHandle(self._handle)
        self._handle = None

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, *exc_info: object) -> None:
        self.release()


def _load_ctypes() -> tuple[types.ModuleType, types.ModuleType]:
    import ctypes
    import ctypes.wintypes

    return ctypes, ctypes.wintypes
