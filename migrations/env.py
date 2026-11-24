"""Alembic environment.

The URL and, when the application drives migrations, the live connection are
provided programmatically through ``config.attributes``. Offline mode is not
used: SQLite migrations run against a real local file.

This module deliberately imports the project :class:`Base` so ``--autogenerate``
sees the metadata, but the application never calls ``create_all``.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    AuditEventRecord,
    BusinessProfileRecord,
    BusinessProfileVersionRecord,
    CatalogueItemRecord,
    LoginThrottleRecord,
    PartyRecord,
    RoleRecord,
    UserRecord,
)

assert BusinessProfileRecord.__tablename__ == "business_profile"
assert BusinessProfileVersionRecord.__tablename__ == "business_profile_versions"
assert AuditEventRecord.__tablename__ == "audit_events"
assert RoleRecord.__tablename__ == "roles"
assert UserRecord.__tablename__ == "users"
assert LoginThrottleRecord.__tablename__ == "login_throttles"
assert PartyRecord.__tablename__ == "parties"
assert CatalogueItemRecord.__tablename__ == "catalogue_items"

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configured_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "No SQLAlchemy URL was supplied. The database path must be injected by the "
            "application or migration tool; Alembic never guesses a location."
        )
    return url


def _run_migrations(connection: object) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using an injected connection or a configured URL."""
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_migrations(connection)
        return

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _configured_url()
    engine = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        with engine.connect() as created_connection:
            _run_migrations(created_connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError(
        "Offline migration mode is not supported for this application. Provide a database file."
    )

run_migrations_online()
