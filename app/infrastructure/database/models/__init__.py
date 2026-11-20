"""Mapped records for approved business tables."""

from __future__ import annotations

from app.infrastructure.database.models.business_profile import (
    AuditEventRecord,
    BusinessProfileRecord,
    BusinessProfileVersionRecord,
)

__all__ = ["AuditEventRecord", "BusinessProfileRecord", "BusinessProfileVersionRecord"]
