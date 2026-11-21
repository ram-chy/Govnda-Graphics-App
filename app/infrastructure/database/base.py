"""Declarative base, metadata, and SQLite file identity constants.

Every ORM model added in later phases must inherit from :class:`Base`. The
explicit naming convention keeps constraint names deterministic so Alembic can
generate stable migration scripts.
"""

from __future__ import annotations

from sqlalchemy import MetaData, event
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.exceptions import DomainRuleError

# SQLite stores ``application_id`` in the database header. The value spells
# "GBGS" in ASCII hex and identifies a Gobindas BMS database independently of
# the schema revision. It is written by the baseline migration, not by runtime
# code.
APPLICATION_ID = 0x47424753

# Application-level schema marker stored in the SQLite header. Alembic remains
# the authority for migration state; this value is a cheap diagnostic marker.
SCHEMA_USER_VERSION = 1

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base with deterministic constraint naming."""

    IMMUTABLE = False
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@event.listens_for(Session, "before_flush")
def _reject_immutable_changes(
    session: Session, flush_context: object, instances: object
) -> None:
    del flush_context, instances
    for instance in (*session.dirty, *session.deleted):
        if getattr(type(instance), "IMMUTABLE", False) is True:
            raise DomainRuleError(
                f"immutable records cannot be changed: {type(instance).__name__}",
                user_message="Audit history is append-only and cannot be changed.",
            )
