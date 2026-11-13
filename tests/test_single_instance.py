"""Single-instance mutex tests (Windows only)."""

from __future__ import annotations

import sys
import uuid

import pytest

from app.core.single_instance import SingleInstanceGuard

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="named mutex is Windows-only")


def _unique_name() -> str:
    return rf"Local\GGBMS.Test.{uuid.uuid4().hex}"


def test_acquire_and_release() -> None:
    guard = SingleInstanceGuard(_unique_name())

    assert guard.is_locked is False
    assert guard.acquire() is True
    assert guard.is_locked is True
    guard.release()
    assert guard.is_locked is False


def test_second_guard_is_refused_until_first_releases() -> None:
    name = _unique_name()
    first = SingleInstanceGuard(name)
    second = SingleInstanceGuard(name)

    try:
        assert first.acquire() is True
        assert second.acquire() is False
        assert second.is_locked is False
    finally:
        first.release()

    try:
        assert second.acquire() is True
    finally:
        second.release()


def test_release_is_idempotent() -> None:
    guard = SingleInstanceGuard(_unique_name())

    guard.release()
    guard.release()
    assert guard.is_locked is False


def test_context_manager_releases() -> None:
    name = _unique_name()
    with SingleInstanceGuard(name) as acquired:
        assert acquired is True

    replacement = SingleInstanceGuard(name)
    try:
        assert replacement.acquire() is True
    finally:
        replacement.release()
