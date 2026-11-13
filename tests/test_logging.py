"""Logging initialisation and rotation configuration tests."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.core import constants
from app.core.logging_config import (
    HANDLER_MARKER,
    CorrelationIdFilter,
    configure_logging,
    new_correlation_id,
)


def _ggbms_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, HANDLER_MARKER, False)
    ]


def test_logging_writes_utf8_log_file(
    tmp_path: Path, clean_logging_handlers: None
) -> None:
    log_file = tmp_path / "logs" / "app.log"

    returned = configure_logging(log_file, level="DEBUG", console=False)
    logging.getLogger("app.test").info(
        "Currency \u20b91,25,000.50", extra={"correlation_id": "abc12345"}
    )
    for handler in _ggbms_handlers():
        handler.flush()

    assert returned == log_file
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Currency \u20b91,25,000.50" in content
    assert "abc12345" in content
    assert "INFO" in content


def test_rotation_settings_are_bounded(tmp_path: Path, clean_logging_handlers: None) -> None:
    log_file = tmp_path / "app.log"

    configure_logging(log_file, max_bytes=1024, backup_count=3)

    handlers = _ggbms_handlers()
    assert len(handlers) == 1
    handler = handlers[0]
    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    assert handler.maxBytes == 1024
    assert handler.backupCount == 3
    assert handler.encoding.lower() == "utf-8"


def test_repeated_configuration_does_not_duplicate_handlers(
    tmp_path: Path, clean_logging_handlers: None
) -> None:
    configure_logging(tmp_path / "app.log")
    configure_logging(tmp_path / "app.log")
    configure_logging(tmp_path / "app.log")

    assert len(_ggbms_handlers()) == 1


def test_invalid_level_is_rejected(tmp_path: Path, clean_logging_handlers: None) -> None:
    with pytest.raises(ValueError):
        configure_logging(tmp_path / "app.log", level="VERBOSE")


def test_configured_level_applies_to_root(tmp_path: Path, clean_logging_handlers: None) -> None:
    configure_logging(tmp_path / "app.log", level="WARNING")

    assert logging.getLogger().level == logging.WARNING


def test_configuration_creates_log_directory(tmp_path: Path, clean_logging_handlers: None) -> None:
    log_file = tmp_path / "nested" / "logs" / "app.log"

    configure_logging(log_file)

    assert log_file.parent.is_dir()


def test_correlation_filter_adds_placeholder() -> None:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    assert CorrelationIdFilter().filter(record) is True
    assert record.correlation_id == "-"


def test_correlation_id_is_short_and_unique() -> None:
    first = new_correlation_id()
    second = new_correlation_id()

    assert len(first) == 8
    assert first != second
    assert int(first, 16) >= 0


def test_default_log_constants_match_documentation() -> None:
    assert constants.LOG_MAX_BYTES == 5 * 1024 * 1024
    assert constants.LOG_BACKUP_COUNT == 5
