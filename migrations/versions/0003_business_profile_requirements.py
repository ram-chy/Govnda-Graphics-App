"""Add approved profile fields, immutable versions, and audit events.

Revision ID: 0003_business_profile_requirements
Revises: 0002_business_profile
Create Date: 2026-11-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_business_profile_requirements"
down_revision: str | None = "0002_business_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VERSIONS_TABLE = "business_profile_versions"
AUDIT_TABLE = "audit_events"
NO_VERSION_UPDATE_TRIGGER = "trg_business_profile_versions_no_update"
NO_VERSION_DELETE_TRIGGER = "trg_business_profile_versions_no_delete"
NO_AUDIT_UPDATE_TRIGGER = "trg_audit_events_no_update"
NO_AUDIT_DELETE_TRIGGER = "trg_audit_events_no_delete"


def upgrade() -> None:
    op.add_column(
        "business_profile",
        sa.Column("secondary_phone", sa.String(length=50), nullable=False, server_default=""),
    )
    op.add_column(
        "business_profile",
        sa.Column("logo_reference", sa.String(length=300), nullable=False, server_default=""),
    )
    op.add_column(
        "business_profile",
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        VERSIONS_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey(
                "business_profile.id",
                name="fk_business_profile_versions_profile_id_business_profile",
            ),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("secondary_phone", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("website", sa.String(length=200), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=False),
        sa.Column("footer_message", sa.String(length=500), nullable=False),
        sa.Column("logo_reference", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "profile_id = 1", name="ck_business_profile_versions_single_profile_versions"
        ),
        sa.CheckConstraint(
            "version_number > 0", name="ck_business_profile_versions_positive_version"
        ),
        sa.UniqueConstraint(
            "profile_id",
            "version_number",
            name="uq_business_profile_versions_unique_profile_version",
        ),
    )

    op.create_table(
        AUDIT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.String(length=2000), nullable=False, server_default="{}"),
    )

    op.execute(
        f"""
        INSERT INTO {VERSIONS_TABLE} (
            profile_id, version_number, business_name, address, phone, secondary_phone,
            email, website, registration_number, footer_message, logo_reference,
            created_at, updated_at
        )
        SELECT 1, 1, business_name, address, phone, secondary_phone, email, website,
               registration_number, footer_message, logo_reference, created_at, updated_at
        FROM business_profile
        WHERE id = 1
          AND NOT EXISTS (
              SELECT 1 FROM {VERSIONS_TABLE} WHERE profile_id = 1 AND version_number = 1
          )
        """
    )
    op.execute("UPDATE business_profile SET version_number = 1 WHERE id = 1 AND version_number = 0")
    op.execute(
        f"""
        INSERT INTO {AUDIT_TABLE} (
            event_type, entity_type, entity_id, actor, created_at, payload
        )
        SELECT 'business_profile.created', 'business_profile', '1',
               'system/unauthenticated', updated_at,
               '{{"reason":"phase_7b_migration_backfill"}}'
        FROM business_profile
        WHERE id = 1
          AND NOT EXISTS (
              SELECT 1 FROM {AUDIT_TABLE}
              WHERE entity_type = 'business_profile' AND entity_id = '1'
          )
        """
    )

    _create_immutable_trigger(NO_VERSION_UPDATE_TRIGGER, VERSIONS_TABLE, "UPDATE")
    _create_immutable_trigger(NO_VERSION_DELETE_TRIGGER, VERSIONS_TABLE, "DELETE")
    _create_immutable_trigger(NO_AUDIT_UPDATE_TRIGGER, AUDIT_TABLE, "UPDATE")
    _create_immutable_trigger(NO_AUDIT_DELETE_TRIGGER, AUDIT_TABLE, "DELETE")


def downgrade() -> None:
    for trigger in (
        NO_VERSION_UPDATE_TRIGGER,
        NO_VERSION_DELETE_TRIGGER,
        NO_AUDIT_UPDATE_TRIGGER,
        NO_AUDIT_DELETE_TRIGGER,
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    op.drop_table(VERSIONS_TABLE)
    op.drop_table(AUDIT_TABLE)
    with op.batch_alter_table("business_profile") as batch:
        batch.drop_column("version_number")
        batch.drop_column("logo_reference")
        batch.drop_column("secondary_phone")


def _create_immutable_trigger(name: str, table: str, action: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER {name}
        BEFORE {action} ON {table}
        BEGIN
            SELECT RAISE(ABORT, 'records are immutable');
        END
        """
    )
