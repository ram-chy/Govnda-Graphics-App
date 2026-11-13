"""Global exception hook tests."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.core.error_handling import install_excepthook
from app.core.logging_config import configure_logging


def test_hook_logs_and_calls_handler(tmp_path: Path, clean_logging_handlers: None) -> None:
    log_file = configure_logging(tmp_path / "app.log")
    captured: list[tuple[str, BaseException]] = []
    original_hook = sys.excepthook

    try:
        hook = install_excepthook(
            lambda correlation_id, exc: captured.append((correlation_id, exc))
        )
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            hook(type(exc), exc, exc.__traceback__)
    finally:
        sys.excepthook = original_hook

    assert len(captured) == 1
    correlation_id, exception = captured[0]
    assert correlation_id
    assert isinstance(exception, RuntimeError)
    assert sys.excepthook is not hook

    content = log_file.read_text(encoding="utf-8")
    assert "Unhandled exception" in content
    assert correlation_id in content
    assert "boom" in content
    assert "RuntimeError" in content


def test_handler_failure_does_not_escape(tmp_path: Path, clean_logging_handlers: None) -> None:
    log_file = configure_logging(tmp_path / "app.log")

    def failing_handler(correlation_id: str, exc: BaseException) -> None:
        raise ValueError("handler failure")

    hook = install_excepthook(failing_handler)
    try:
        raise RuntimeError("original failure")
    except RuntimeError as exc:
        # Must not raise even though the UI handler fails.
        hook(type(exc), exc, exc.__traceback__)

    content = log_file.read_text(encoding="utf-8")
    assert "original failure" in content
    assert "The fatal error handler itself failed" in content


def test_keyboard_interrupt_uses_default_hook(
    tmp_path: Path, monkeypatch, clean_logging_handlers: None
) -> None:
    configure_logging(tmp_path / "app.log")
    captured: list[type[BaseException]] = []
    monkeypatch.setattr(
        sys,
        "__excepthook__",
        lambda exc_type, exc, tb: captured.append(exc_type),
    )
    hook = install_excepthook(lambda correlation_id, exc: None)

    hook(KeyboardInterrupt, KeyboardInterrupt(), None)

    assert captured == [KeyboardInterrupt]


def test_hook_without_handler_logs_only(tmp_path: Path, clean_logging_handlers: None) -> None:
    log_file = configure_logging(tmp_path / "app.log")
    hook = install_excepthook(None)

    try:
        raise LookupError("no ui handler")
    except LookupError as exc:
        hook(type(exc), exc, exc.__traceback__)

    assert "no ui handler" in log_file.read_text(encoding="utf-8")
    assert logging.getLogger().level <= logging.CRITICAL
