"""Mapped records for approved business tables."""

from __future__ import annotations

from app.infrastructure.database.models.auth import (
    LoginThrottleRecord,
    RoleRecord,
    UserRecord,
)
from app.infrastructure.database.models.business_profile import (
    AuditEventRecord,
    BusinessProfileRecord,
    BusinessProfileVersionRecord,
)
from app.infrastructure.database.models.party import PartyRecord

__all__ = [
    "AuditEventRecord",
    "BusinessProfileRecord",
    "BusinessProfileVersionRecord",
    "LoginThrottleRecord",
    "PartyRecord",
    "RoleRecord",
    "UserRecord",
]
