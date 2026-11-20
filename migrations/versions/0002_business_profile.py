"""Add the approved single-row business profile.

Revision ID: 0002_business_profile
Revises: 0001_baseline
Create Date: 2026-11-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_business_profile"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("website", sa.String(length=200), nullable=False, server_default=""),
        sa.Column(
            "registration_number", sa.String(length=100), nullable=False, server_default=""
        ),
        sa.Column("footer_message", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_business_profile_single_row"),
    )


def downgrade() -> None:
    op.drop_table("business_profile")
