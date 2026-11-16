"""Background job helpers shared by the Phase 4 view models.

Jobs are plain callables that receive a progress callback. All business work
inside a job is Qt-free; this module only moves the result back to the GUI thread
through queued signals. A replacement runner is supplied by tests so the same
view-model code can be exercised without a thread pool.

Callbacks are connected *before* a task starts, so a fast job cannot finish
before the view model is listening.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from app.core.exceptions import DEFAULT_USER_MESSAGE, AppError

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]
Job = Callable[[ProgressCallback], object]
SuccessCallback = Callable[[object], None]
FailureCallback = Callable[[str, str], None]


class TaskSignals(QObject):
    """Signals emitted by one background job."""

    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str, str)


class BackgroundTask(QRunnable):
    """Run one job and translate its outcome into signals."""

    def __init__(self, job: Job) -> None:
        super().__init__()
        self._job = job
        self.signals = TaskSignals()
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            result = self._job(self.signals.progress.emit)
        except AppError as exc:
            logger.warning("Background operation failed: %s", exc)
            self.signals.failed.emit(exc.user_message, str(exc))
        except Exception as exc:  # noqa: BLE001 - worker boundary
            logger.exception("Background operation failed unexpectedly")
            self.signals.failed.emit(DEFAULT_USER_MESSAGE, str(exc))
        else:
            self.signals.succeeded.emit(result)


class TaskRunner(Protocol):
    """Minimal interface used by view models."""

    def submit(
        self,
        job: Job,
        *,
        on_progress: ProgressCallback,
        on_success: SuccessCallback,
        on_failure: FailureCallback,
    ) -> None: ...


class ThreadTaskRunner(QObject):
    """Serialise jobs on one worker thread.

    One worker is deliberate: SQLite has a single writer and the operation lock
    already rejects conflicting processes. Queueing here keeps the UI thread
    responsive without creating competing writers inside this process.
    """

    def __init__(self, parent: QObject | None = None, *, max_threads: int = 1) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max(1, max_threads))
        self._live: set[TaskSignals] = set()

    def submit(
        self,
        job: Job,
        *,
        on_progress: ProgressCallback,
        on_success: SuccessCallback,
        on_failure: FailureCallback,
    ) -> None:
        task = BackgroundTask(job)
        signals = task.signals
        self._live.add(signals)
        signals.progress.connect(on_progress)
        signals.succeeded.connect(on_success)
        signals.failed.connect(on_failure)
        signals.succeeded.connect(lambda _result, s=signals: self._release(s))
        signals.failed.connect(lambda _message, _detail, s=signals: self._release(s))
        self._pool.start(task)

    def wait_for_done(self, timeout_ms: int = 30_000) -> bool:
        return self._pool.waitForDone(timeout_ms)

    def _release(self, signals: TaskSignals) -> None:
        self._live.discard(signals)


class InlineTaskRunner:
    """Run jobs on the calling thread; used by tests and smoke checks."""

    def submit(
        self,
        job: Job,
        *,
        on_progress: ProgressCallback,
        on_success: SuccessCallback,
        on_failure: FailureCallback,
    ) -> None:
        task = BackgroundTask(job)
        task.signals.progress.connect(on_progress)
        task.signals.succeeded.connect(on_success)
        task.signals.failed.connect(on_failure)
        task.run()


__all__ = [
    "BackgroundTask",
    "FailureCallback",
    "InlineTaskRunner",
    "Job",
    "ProgressCallback",
    "SuccessCallback",
    "TaskRunner",
    "TaskSignals",
    "ThreadTaskRunner",
]
