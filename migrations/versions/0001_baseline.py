"""Baseline schema identity.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-13

Phase 2 creates no application tables by design: business tables are added only
after their module rules and fields are approved. This migration establishes
the database file identity so the application can refuse an unrelated SQLite
file without inspecting table names.

* ``application_id`` is a fixed 32-bit header marker ("GBGS").
* ``user_version`` starts at 1 for human-readable diagnostics only. Alembic's
  ``alembic_version`` table remains the authority for migration state.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.infrastructure.database.base import APPLICATION_ID, SCHEMA_USER_VERSION

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    op.execute(f"PRAGMA user_version = {SCHEMA_USER_VERSION}")


def downgrade() -> None:
    op.execute("PRAGMA user_version = 0")
    op.execute("PRAGMA application_id = 0")
