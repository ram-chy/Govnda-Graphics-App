"""Explicit dependency wiring for the application root (composition root).

The live database is held through a :class:`DatabaseRuntime` because restore and
relocation replace the file while the application keeps running. The UI never
captures an engine directly; it asks the runtime for the current one after an
operation completes.

Backup, restore, relocation, and schedule use cases are constructed by a
:class:`BackupWorkspaceFactory` bound to the same runtime. The factory is kept on
the context so the window can rebuild a workspace after relocation without
re-reading anything from a working directory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import AppConfig, ConfigService
from app.core.paths import AppPaths
from app.infrastructure.database.config import DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.migrations import verify_database_for_startup
from app.services.auth_services import AuthServices
from app.services.backup_workspace import BackupWorkspace, BackupWorkspaceFactory
from app.services.business_profile_service import BusinessProfileServiceFactory
from app.services.catalogue_service import CatalogueServiceFactory
from app.services.database_runtime import DatabaseRuntime
from app.services.party_service import PartyServiceFactory

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppContext:
    """Objects constructed at startup and passed explicitly to the UI.

    ``runtime.database`` is ``None`` when no database has been configured yet.
    The application never invents a path, so Phase 1 startup behaviour is
    preserved exactly until the setup wizard records one.
    """

    paths: AppPaths
    config: AppConfig
    config_service: ConfigService
    runtime: DatabaseRuntime = field(default_factory=DatabaseRuntime)
    workspace_factory: BackupWorkspaceFactory = field(init=False)
    business_profile_factory: BusinessProfileServiceFactory = field(init=False)
    party_factory: PartyServiceFactory = field(init=False)
    catalogue_factory: CatalogueServiceFactory = field(init=False)
    auth_services: AuthServices | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        auth_services: AuthServices | None = None
        if self.runtime.database is not None:
            auth_services = AuthServices.create(
                self.runtime,
                idle_timeout_seconds=self.config.idle_timeout_seconds,
            )
        object.__setattr__(self, "auth_services", auth_services)
        object.__setattr__(
            self,
            "workspace_factory",
            BackupWorkspaceFactory(
                self.config_service,
                self.runtime,
                auth_services=auth_services,
            ),
        )
        object.__setattr__(
            self,
            "business_profile_factory",
            BusinessProfileServiceFactory(
                self.config_service,
                self.runtime,
                auth_services=auth_services,
            ),
        )
        object.__setattr__(
            self,
            "party_factory",
            PartyServiceFactory(
                self.runtime,
                auth_services=auth_services,
            ),
        )
        object.__setattr__(
            self,
            "catalogue_factory",
            CatalogueServiceFactory(
                self.runtime,
                auth_services=auth_services,
            ),
        )

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
        runtime: DatabaseRuntime | None = None,
    ) -> AppContext:
        """Build a context from an already assessed configuration and database."""
        active = runtime or DatabaseRuntime()
        if database is not None:
            active.install(database)
        return cls(
            paths=paths,
            config=config,
            config_service=config_service,
            runtime=active,
        )

    @property
    def database(self) -> Database | None:
        return self.runtime.database

    @property
    def database_path(self) -> Path | None:
        return self.runtime.path

    @property
    def workspace(self) -> BackupWorkspace | None:
        """Return the current backup workspace, if configuration supports one."""
        return self.workspace_factory.build_optional()

    def close(self) -> None:
        """Release pooled database connections. Safe to call more than once."""
        if self.auth_services is not None:
            self.auth_services.end_session()
        self.runtime.close()


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


__all__ = ["AppContext"]
