"""Global exception handling.

Unexpected exceptions are logged with a correlation ID and a traceback. The
optional UI handler receives only the ID and the exception, so it can show a
safe message without exposing technical details.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from types import TracebackType

from app.core.logging_config import new_correlation_id

logger = logging.getLogger(__name__)

type ErrorHandler = Callable[[str, BaseException], None]
type ExceptionHook = Callable[
    [type[BaseException], BaseException, TracebackType | None], None
]


def install_excepthook(handler: ErrorHandler | None = None) -> ExceptionHook:
    """Install a logging ``sys.excepthook`` and return it.

    KeyboardInterrupt is delegated to the default hook so console users can
    still interrupt a stuck development run.
    """

    def _hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        correlation_id = new_correlation_id()
        logger.critical(
            "Unhandled exception [%s]: %s",
            correlation_id,
            exc_value,
            exc_info=(exc_type, exc_value, exc_traceback),
            extra={"correlation_id": correlation_id},
        )
        if handler is not None:
            try:
                handler(correlation_id, exc_value)
            except Exception:
                logger.exception("The fatal error handler itself failed")

    sys.excepthook = _hook
    return _hook
