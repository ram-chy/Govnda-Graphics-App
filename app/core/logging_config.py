"""Centralized logging configuration.

Logs are written to ``%LOCALAPPDATA%\\GobindasBMS\\logs`` and rotate at 5 MB
with five retained files (ADR-018). The console handler is intended for
development only. Log messages must not contain personal or financial data.
"""

from __future__ import annotations

import logging
import sys
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core import constants

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [%(correlation_id)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
HANDLER_MARKER = "_ggbms_handler"


class CorrelationIdFilter(logging.Filter):
    """Ensure every record has a correlation ID, using ``-`` when absent."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "correlation_id", None):
            record.correlation_id = "-"
        return True


def new_correlation_id() -> str:
    """Return a short, non-guessable ID used to link a user message to a log entry."""
    return uuid.uuid4().hex[:8]


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    resolved = logging.getLevelNamesMapping().get(level.upper())
    if resolved is None:
        raise ValueError(f"unknown log level: {level!r}")
    return resolved


def configure_logging(
    log_file: Path,
    *,
    level: str | int = constants.DEFAULT_LOG_LEVEL,
    console: bool = False,
    max_bytes: int = constants.LOG_MAX_BYTES,
    backup_count: int = constants.LOG_BACKUP_COUNT,
) -> Path:
    """Configure root logging and return the active log file path.

    Previously installed GGBMS handlers are removed first, so repeated calls
    (tests, restart flows) do not duplicate output. Handlers installed by other
    libraries or test runners are left untouched.
    """
    resolved_level = _resolve_level(level)
    log_path = Path(log_file)

    root = logging.getLogger()
    root.setLevel(resolved_level)

    for handler in list(root.handlers):
        if getattr(handler, HANDLER_MARKER, False):
            root.removeHandler(handler)
            handler.close()

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    except OSError:
        # Never let logging setup prevent the application from starting.
        logging.getLogger(__name__).warning(
            "File logging could not be configured for %s", log_path, exc_info=True
        )
        return log_path

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(CorrelationIdFilter())
    setattr(file_handler, HANDLER_MARKER, True)
    root.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(CorrelationIdFilter())
        setattr(console_handler, HANDLER_MARKER, True)
        root.addHandler(console_handler)

    return log_path
