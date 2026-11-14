"""SQLAlchemy engine and database lifecycle for SQLite.

One engine is created per configured database path. Connections are short-lived
and always carry the approved PRAGMA profile (ARCHITECTURE.md ADR-008). The
application is single-user and SQLite is single-writer by design; sessions are
never shared between threads.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.exceptions import DatabaseUnavailableError
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.errors import (
    classify_database_error,
    to_database_unavailable,
    user_message_for,
)
from app.infrastructure.database.session import UnitOfWork

logger = logging.getLogger(__name__)

# Small pool: a desktop workstation needs one connection for the GUI and at
# most one short-lived worker connection. Extra connections queue rather than
# silently multiplying writers.
POOL_SIZE = 2
MAX_OVERFLOW = 0

PRAGMA_STATEMENTS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA busy_timeout = {busy_timeout_ms}",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = FULL",
    "PRAGMA wal_autocheckpoint = 1000",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA trusted_schema = OFF",
)


def _apply_sqlite_pragmas(dbapi_connection: object, busy_timeout_ms: int) -> None:
    """Apply the approved connection profile to one new DB-API connection."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        for template in PRAGMA_STATEMENTS:
            cursor.execute(template.format(busy_timeout_ms=busy_timeout_ms))
        row = cursor.execute("PRAGMA journal_mode").fetchone()
        mode = str(row[0]).lower() if row else ""
        if mode != "wal":
            raise sqlite3.OperationalError(
                f"SQLite did not enable WAL mode (reported {mode or 'unknown'})"
            )
        row = cursor.execute("PRAGMA foreign_keys").fetchone()
        if not row or int(row[0]) != 1:
            raise sqlite3.OperationalError("SQLite foreign-key enforcement is not enabled")
    finally:
        cursor.close()


def _pragma_listener(busy_timeout_ms: int) -> Callable[[object, object], None]:
    def listener(dbapi_connection: object, connection_record: object) -> None:
        del connection_record
        _apply_sqlite_pragmas(dbapi_connection, busy_timeout_ms)

    return listener


def create_sqlite_engine(config: DatabaseConfig) -> Engine:
    """Create an engine with the project PRAGMA profile and a small pool."""
    engine = create_engine(
        config.url,
        connect_args={
            "timeout": config.busy_timeout_seconds,
            # Sessions are never shared across threads, but a pooled connection
            # may be checked out by a worker thread. SQLAlchemy already sets
            # this for file databases; making it explicit documents the policy.
            "check_same_thread": False,
        },
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=config.busy_timeout_seconds,
        pool_pre_ping=True,
        future=True,
    )
    event.listen(engine, "connect", _pragma_listener(config.busy_timeout_ms))
    return engine


class Database:
    """Owns one engine and session factory for a configured database path."""

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._engine = create_sqlite_engine(config)
        self._session_factory = sessionmaker(
            bind=self._engine,
            class_=Session,
            expire_on_commit=False,
            future=True,
        )
        self._disposed = False

    @property
    def config(self) -> DatabaseConfig:
        return self._config

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        return self._session_factory

    def unit_of_work(self) -> UnitOfWork:
        """Return a new short transaction scope. One use case = one UoW."""
        return UnitOfWork(self._session_factory)

    def sqlite_version(self) -> str:
        with self._engine.connect() as connection:
            value = connection.exec_driver_sql("SELECT sqlite_version()").scalar_one()
        return str(value)

    def verify_accessible(self) -> None:
        """Confirm the file exists and accepts a trivial query.

        This method never creates the database and never scans its contents.
        """
        self._config.require_existing_file()
        try:
            with self._engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
        except (SQLAlchemyError, sqlite3.Error, OSError) as exc:
            kind = classify_database_error(exc)
            if kind == "unknown":
                raise to_database_unavailable(exc, self._config.path) from exc
            raise DatabaseUnavailableError(
                f"database access failed ({kind}) for {self._config.path}: {exc}",
                user_message=user_message_for(kind, self._config.path),
            ) from exc

    def shutdown(self) -> None:
        """Checkpoint the WAL (best effort) and close all pooled connections."""
        if self._disposed:
            return
        self._disposed = True
        if self._config.path.exists():
            try:
                with self._engine.connect() as connection:
                    connection.exec_driver_sql("PRAGMA wal_checkpoint(PASSIVE)")
            except (SQLAlchemyError, sqlite3.Error, OSError):
                logger.warning(
                    "WAL checkpoint on shutdown failed for %s", self._config.path, exc_info=True
                )
        self._engine.dispose()
        logger.debug("Database engine disposed for %s", self._config.path)

    def __enter__(self) -> Database:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback
        self.shutdown()


__all__ = [
    "Database",
    "MAX_OVERFLOW",
    "POOL_SIZE",
    "PRAGMA_STATEMENTS",
    "create_sqlite_engine",
]
