"""Audit event values for significant business-profile operations."""

from __future__ import annotations

from dataclasses import dataclass

UNAUTHENTICATED_ACTOR = "system/unauthenticated"
PROFILE_ENTITY_TYPE = "business_profile"


class ProfileAuditEventType:
    CREATED = "business_profile.created"
    UPDATED = "business_profile.updated"
    LOGO_CHANGED = "business_profile.logo_changed"
    HISTORY_VIEWED = "business_profile.history_viewed"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    created_at: str
    payload: str = "{}"


__all__ = [
    "PROFILE_ENTITY_TYPE",
    "UNAUTHENTICATED_ACTOR",
    "AuditEvent",
    "ProfileAuditEventType",
]
