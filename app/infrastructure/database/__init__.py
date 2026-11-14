"""Database infrastructure: engine, sessions, migrations, and diagnostics."""

from __future__ import annotations

from app.infrastructure.database.base import APPLICATION_ID, NAMING_CONVENTION, Base
from app.infrastructure.database.config import DEFAULT_BUSY_TIMEOUT_MS, DatabaseConfig
from app.infrastructure.database.engine import Database
from app.infrastructure.database.health import (
    DatabaseDiagnostics,
    DatabaseHealthReport,
    DatabaseHealthStatus,
)
from app.infrastructure.database.migrations import (
    MigrationManager,
    MigrationState,
    MigrationStatus,
    verify_database_for_startup,
)
from app.infrastructure.database.repository import Repository
from app.infrastructure.database.session import UnitOfWork

__all__ = [
    "APPLICATION_ID",
    "DEFAULT_BUSY_TIMEOUT_MS",
    "Base",
    "Database",
    "DatabaseConfig",
    "DatabaseDiagnostics",
    "DatabaseHealthReport",
    "DatabaseHealthStatus",
    "MigrationManager",
    "MigrationState",
    "MigrationStatus",
    "NAMING_CONVENTION",
    "Repository",
    "UnitOfWork",
    "verify_database_for_startup",
]
