"""Explicit unit-of-work transaction boundary.

A session is created lazily when first used and always closed when the scope
ends. Commit is explicit: leaving the block without ``commit()`` rolls back.
Any exception rolls back before it propagates. This is intentionally stricter
than "auto-commit on success", because a forgotten commit must never publish a
partial financial operation by accident.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


class UnitOfWork:
    """One short transaction. Nesting is forbidden by convention."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed = False
        self._closed = False

    @property
    def session(self) -> Session:
        """Return the session, creating it on first use."""
        if self._closed:
            raise RuntimeError("unit of work is already closed")
        if self._session is None:
            self._session = self._session_factory()
        return self._session

    @property
    def committed(self) -> bool:
        return self._committed

    def commit(self) -> None:
        """Commit the current transaction, rolling back if the commit fails."""
        if self._closed:
            raise RuntimeError("unit of work is already closed")
        session = self.session
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        self._committed = True

    def rollback(self) -> None:
        """Roll back the current transaction if one is active."""
        if self._session is None or self._closed:
            return
        try:
            if self._session.in_transaction():
                self._session.rollback()
        except Exception:
            logger.warning("Rollback failed during unit-of-work cleanup", exc_info=True)

    def close(self) -> None:
        """Roll back anything left open and return the connection to the pool."""
        if self._closed:
            return
        if self._session is not None:
            try:
                if self._session.in_transaction():
                    self._session.rollback()
            except Exception:
                logger.warning("Rollback failed while closing session", exc_info=True)
            finally:
                self._session.close()
        self._closed = True

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self.close()
        return False  # never suppress an exception


__all__ = ["UnitOfWork"]
