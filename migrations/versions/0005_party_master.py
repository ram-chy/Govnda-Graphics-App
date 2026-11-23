"""Add customer and supplier master records.

Revision ID: 0005_party_master
Revises: 0004_authentication
Create Date: 2026-11-23

Phase 9 scope: basic party identity/contact fields, active flag, and append-only
audit-event usage through the existing audit_events table. No financial tables,
transactions, opening balances, or hard-delete workflow are introduced.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_party_master"
down_revision: str | None = "0004_authentication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PARTIES_TABLE = "parties"


def upgrade() -> None:
    op.create_table(
        PARTIES_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("party_kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_key", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("contact_person", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("notes", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "party_kind IN ('customer', 'supplier')",
            name="ck_parties_kind",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_parties_name_not_empty"),
        sa.CheckConstraint("is_active IN (0, 1)", name="ck_parties_is_active_bool"),
    )
    op.create_index("ix_parties_kind_name_key", PARTIES_TABLE, ["party_kind", "name_key"])
    op.create_index("ix_parties_kind_phone", PARTIES_TABLE, ["party_kind", "phone"])
    op.create_index("ix_parties_kind_is_active", PARTIES_TABLE, ["party_kind", "is_active"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if PARTIES_TABLE in inspector.get_table_names():
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {PARTIES_TABLE}")).scalar_one()
        if int(count) > 0:
            raise RuntimeError(
                "Refusing to downgrade 0005_party_master while party records exist; "
                "downgrade would destroy customer/supplier master data."
            )
    op.drop_index("ix_parties_kind_is_active", table_name=PARTIES_TABLE)
    op.drop_index("ix_parties_kind_phone", table_name=PARTIES_TABLE)
    op.drop_index("ix_parties_kind_name_key", table_name=PARTIES_TABLE)
    op.drop_table(PARTIES_TABLE)
