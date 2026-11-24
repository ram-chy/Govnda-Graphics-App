"""Add product and service catalogue master records.

Revision ID: 0006_catalogue_master
Revises: 0005_party_master
Create Date: 2026-11-24

Phase 10 scope: basic catalogue identity/pricing-reference fields, active flag,
and append-only audit-event usage through the existing audit_events table.
No inventory, stock movement, variants, barcodes, tax, transactions, or
hard-delete workflow are introduced.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_catalogue_master"
down_revision: str | None = "0005_party_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATALOGUE_TABLE = "catalogue_items"


def upgrade() -> None:
    op.create_table(
        CATALOGUE_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_key", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("default_sale_price_minor", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint("kind IN ('product', 'service')", name="ck_catalogue_items_kind"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_catalogue_items_name_not_empty"),
        sa.CheckConstraint("is_active IN (0, 1)", name="ck_catalogue_items_is_active_bool"),
        sa.CheckConstraint(
            "default_sale_price_minor IS NULL OR default_sale_price_minor >= 0",
            name="ck_catalogue_items_price_non_negative",
        ),
    )
    op.create_index("ix_catalogue_items_kind_name_key", CATALOGUE_TABLE, ["kind", "name_key"])
    op.create_index("ix_catalogue_items_kind_is_active", CATALOGUE_TABLE, ["kind", "is_active"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if CATALOGUE_TABLE in inspector.get_table_names():
        count = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {CATALOGUE_TABLE}")
        ).scalar_one()
        if int(count) > 0:
            raise RuntimeError(
                "Refusing to downgrade 0006_catalogue_master while catalogue records exist; "
                "downgrade would destroy product/service master data."
            )
    op.drop_index("ix_catalogue_items_kind_is_active", table_name=CATALOGUE_TABLE)
    op.drop_index("ix_catalogue_items_kind_name_key", table_name=CATALOGUE_TABLE)
    op.drop_table(CATALOGUE_TABLE)
