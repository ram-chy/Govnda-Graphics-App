"""Mutable holder for the application's live database.

Restore and relocation replace the database file while the application keeps
running. The composition root and the UI therefore must not capture a
:class:`~app.infrastructure.database.engine.Database` instance directly: they
hold a :class:`DatabaseRuntime` and ask it for the current engine. Business
services are Qt-free; the UI re-reads the runtime after an operation.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from app.core.exceptions import DatabaseUnavailableError
from app.infrastructure.database.engine import Database

logger = logging.getLogger(__name__)


class DatabaseRuntime:
    """Thread-safe, replaceable reference to the open application database."""

    def __init__(self, database: Database | None = None) -> None:
        self._lock = threading.RLock()
        self._database = database

    @property
    def database(self) -> Database | None:
        with self._lock:
            return self._database

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._database is not None

    @property
    def path(self) -> Path | None:
        with self._lock:
            return self._database.config.path if self._database is not None else None

    def require(self) -> Database:
        """Return the open database or raise a user-facing error."""
        with self._lock:
            if self._database is None:
                raise DatabaseUnavailableError(
                    "no database is open",
                    user_message=(
                        "The database is not open. No backup or restore action can run until "
                        "the application has connected to a database."
                    ),
                )
            return self._database

    def install(self, database: Database) -> Database | None:
        """Make ``database`` current and return the previous instance.

        The previous instance is not shut down here: the caller decides when to
        close it. Restore closes the engine before replacing the file, then
        installs the reopened engine.
        """
        with self._lock:
            previous = self._database
            self._database = database
            logger.info("Database runtime now points at %s", database.config.path)
            return previous

    def close(self) -> None:
        """Dispose the current engine and leave the runtime empty."""
        with self._lock:
            database = self._database
            self._database = None
        if database is not None:
            database.shutdown()
            logger.info("Database runtime closed %s", database.config.path)

    def close_and_dispose(self) -> Path | None:
        """Close the engine and return the path it pointed at."""
        with self._lock:
            database = self._database
            self._database = None
        if database is None:
            return None
        path = database.config.path
        database.shutdown()
        logger.info("Database runtime released %s for replacement", path)
        return path

    def __enter__(self) -> DatabaseRuntime:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


__all__ = ["DatabaseRuntime"]
