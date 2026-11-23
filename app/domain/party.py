"""Customer and Supplier master-data domain rules.

Phase 9 scope is intentionally small: identify parties, keep contact details,
support activate/deactivate, and prevent unsafe deletion. No financial ledger,
opening balance, credit limit, tax, pricing, or transaction behavior is included.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_NAME_LENGTH = 200
MAX_PHONE_LENGTH = 50
MAX_EMAIL_LENGTH = 200
MAX_ADDRESS_LENGTH = 500
MAX_CONTACT_PERSON_LENGTH = 200
MAX_NOTES_LENGTH = 1000


class PartyKind(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"

    @property
    def label(self) -> str:
        return "Customer" if self is PartyKind.CUSTOMER else "Supplier"


class PartyAuditEventType(StrEnum):
    CREATED = "party.created"
    UPDATED = "party.updated"
    ACTIVATED = "party.activated"
    DEACTIVATED = "party.deactivated"


PARTY_ENTITY_TYPE = "party"


def normalize_party_name(name: str) -> str:
    return " ".join(name.strip().split())


def party_name_key(name: str) -> str:
    return normalize_party_name(name).casefold()


def normalize_optional(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())


def normalize_phone(value: str | None) -> str:
    if value is None:
        return ""
    # Keep user-entered formatting light; collapse whitespace for stable storage.
    return " ".join(value.strip().split())


@dataclass(frozen=True, slots=True)
class Party:
    party_id: int | None
    kind: PartyKind
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    contact_person: str = ""
    notes: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    @property
    def name_key(self) -> str:
        return party_name_key(self.name)

    def normalized(self) -> Party:
        return Party(
            party_id=self.party_id,
            kind=self.kind,
            name=normalize_party_name(self.name),
            phone=normalize_phone(self.phone),
            email=normalize_optional(self.email),
            address=normalize_optional(self.address),
            contact_person=normalize_optional(self.contact_person),
            notes=normalize_optional(self.notes),
            is_active=bool(self.is_active),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(frozen=True, slots=True)
class PartyValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PartyDuplicateWarning:
    reason: str
    existing_id: int
    existing_name: str


def validate_party(party: Party) -> PartyValidationResult:
    p = party.normalized()
    errors: list[str] = []
    if not p.name:
        errors.append("Name is required.")
    if len(p.name) > MAX_NAME_LENGTH:
        errors.append(f"Name must be at most {MAX_NAME_LENGTH} characters.")
    if len(p.phone) > MAX_PHONE_LENGTH:
        errors.append(f"Phone must be at most {MAX_PHONE_LENGTH} characters.")
    if len(p.email) > MAX_EMAIL_LENGTH:
        errors.append(f"Email must be at most {MAX_EMAIL_LENGTH} characters.")
    if len(p.address) > MAX_ADDRESS_LENGTH:
        errors.append(f"Address must be at most {MAX_ADDRESS_LENGTH} characters.")
    if len(p.contact_person) > MAX_CONTACT_PERSON_LENGTH:
        errors.append(
            f"Contact person must be at most {MAX_CONTACT_PERSON_LENGTH} characters."
        )
    if len(p.notes) > MAX_NOTES_LENGTH:
        errors.append(f"Notes must be at most {MAX_NOTES_LENGTH} characters.")
    return PartyValidationResult(valid=not errors, errors=tuple(errors))


__all__ = [
    "MAX_ADDRESS_LENGTH",
    "MAX_CONTACT_PERSON_LENGTH",
    "MAX_EMAIL_LENGTH",
    "MAX_NAME_LENGTH",
    "MAX_NOTES_LENGTH",
    "MAX_PHONE_LENGTH",
    "PARTY_ENTITY_TYPE",
    "Party",
    "PartyAuditEventType",
    "PartyDuplicateWarning",
    "PartyKind",
    "PartyValidationResult",
    "normalize_optional",
    "normalize_party_name",
    "normalize_phone",
    "party_name_key",
    "validate_party",
]
