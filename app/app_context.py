"""Explicit dependency wiring for the application root (composition root)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.config import AppConfig, ConfigService
from app.core.paths import AppPaths
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import verify_database_for_startup

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppContext:
    """Objects constructed at startup and passed explicitly to the UI.

    ``database`` is ``None`` when no database has been configured yet. The
    application never invents a path, so Phase 1 startup behaviour is preserved
    exactly until the setup wizard records one.
    """

    paths: AppPaths
    config: AppConfig
    config_service: ConfigService
    database: Database | None = None

    @classmethod
    def create(cls, paths: AppPaths) -> AppContext:
        """Open a previously configured database, or return an unconfigured context.

        Startup in :mod:`app.main` uses :class:`~app.services.startup_service.StartupService`
        and :meth:`from_parts` so first-launch setup and recovery are handled before
        this context is built. This method remains useful for tests and tools that
        already know configuration exists.
        """
        config_service = ConfigService(paths.config_file)
        config = config_service.load()
        database = _open_configured_database(config)
        return cls.from_parts(
            paths,
            config=config,
            config_service=config_service,
            database=database,
        )

    @classmethod
    def from_parts(
        cls,
        paths: AppPaths,
        *,
        config: AppConfig,
        config_service: ConfigService,
        database: Database | None,
    ) -> AppContext:
        """Build a context from an already assessed configuration and database."""
        return cls(
            paths=paths,
            config=config,
            config_service=config_service,
            database=database,
        )

    @property
    def database_path(self) -> Path | None:
        return self.database.config.path if self.database is not None else None

    def close(self) -> None:
        """Release pooled database connections. Safe to call more than once."""
        if self.database is not None:
            self.database.shutdown()


def _open_configured_database(config: AppConfig) -> Database | None:
    """Open and validate the configured database without upgrading it.

    A database file is never created here. If validation fails, the engine is
    disposed before the error propagates so a failed startup leaves no
    half-open connection behind.
    """
    if config.database_path is None:
        return None

    database = Database(DatabaseConfig(path=Path(config.database_path)))
    try:
        verify_database_for_startup(database)
    except BaseException:
        database.shutdown()
        raise
    logger.info("Configured database opened: %s", database.config.path)
    return database
