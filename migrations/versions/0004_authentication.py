"""Add local user accounts, approved roles, and login throttling.

Revision ID: 0004_authentication
Revises: 0003_business_profile_requirements
Create Date: 2026-11-22

Forward-only in practice: no user or role is seeded, and no existing table,
Business Profile record, or audit row is modified. Roles are reference data;
user accounts are created only through the first-run workflow.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_authentication"
down_revision: str | None = "0003_business_profile_requirements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES_TABLE = "roles"
USERS_TABLE = "users"
THROTTLES_TABLE = "login_throttles"

APPROVED_ROLES = (
    ("owner_admin", "Owner/Admin"),
    ("operator", "Operator"),
    ("accountant_reviewer", "Accountant/Reviewer"),
    ("viewer", "Viewer"),
)


def upgrade() -> None:
    op.create_table(
        ROLES_TABLE,
        sa.Column("key", sa.String(length=50), primary_key=True),
        sa.Column("display_name", sa.String(length=100), nullable=False),
    )

    op.create_table(
        USERS_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("username_key", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=1000), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "role_key",
            sa.String(length=50),
            sa.ForeignKey(f"{ROLES_TABLE}.key", name="fk_users_role_key_roles"),
            nullable=False,
        ),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint("is_active IN (0, 1)", name="ck_users_active_flag"),
        sa.CheckConstraint(
            "role_key IN ('owner_admin', 'operator', 'accountant_reviewer', 'viewer')",
            name="ck_users_approved_role",
        ),
        sa.UniqueConstraint("username_key", name="uq_users_case_insensitive_username"),
    )
    op.create_index("ix_users_role_key", USERS_TABLE, ["role_key"])
    op.create_index("ix_users_is_active", USERS_TABLE, ["is_active"])

    op.create_table(
        THROTTLES_TABLE,
        sa.Column("username_key", sa.String(length=100), primary_key=True),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_failed_at", sa.String(length=32), nullable=False),
        sa.Column("cooldown_until", sa.String(length=32), nullable=True),
        sa.CheckConstraint("failed_count >= 0", name="ck_login_throttles_non_negative_count"),
    )

    for key, display_name in APPROVED_ROLES:
        op.execute(
            f"""
            INSERT INTO {ROLES_TABLE} (key, display_name)
            SELECT '{key}', '{display_name}'
            WHERE NOT EXISTS (SELECT 1 FROM {ROLES_TABLE} WHERE key = '{key}')
            """
        )


def downgrade() -> None:
    # This revision is forward-only in normal operation. An explicit downgrade
    # is refused once accounts or audit history exist so no authentication data
    # or append-only record can be removed by a tooling mistake.
    connection = op.get_bind()
    account_count = connection.exec_driver_sql(f"SELECT COUNT(*) FROM {USERS_TABLE}").scalar_one()
    audit_count = connection.exec_driver_sql("SELECT COUNT(*) FROM audit_events").scalar_one()
    if int(account_count) or int(audit_count):
        raise RuntimeError(
            "Refusing to downgrade authentication schema while user accounts or "
            "append-only audit history exist."
        )
    op.drop_index("ix_users_is_active", table_name=USERS_TABLE)
    op.drop_index("ix_users_role_key", table_name=USERS_TABLE)
    op.drop_table(THROTTLES_TABLE)
    op.drop_table(USERS_TABLE)
    op.drop_table(ROLES_TABLE)
