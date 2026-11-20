"""Approved business-profile domain rules and immutable history snapshots."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from enum import StrEnum

SINGLE_PROFILE_ID = 1

FIELD_LABELS: dict[str, str] = {
    "business_name": "Business name",
    "address": "Address",
    "phone": "Phone",
    "secondary_phone": "Secondary phone",
    "email": "Email",
    "website": "Website",
    "registration_number": "Registration number",
    "footer_message": "Footer message",
    "logo": "Logo",
}

MANDATORY_TEXT_FIELDS: tuple[str, ...] = (
    "business_name",
    "address",
    "phone",
    "email",
    "footer_message",
)

OPTIONAL_FIELDS: tuple[str, ...] = (
    "secondary_phone",
    "website",
    "registration_number",
)

PROFILE_FIELDS: tuple[str, ...] = MANDATORY_TEXT_FIELDS + OPTIONAL_FIELDS


class ProfileStatus(StrEnum):
    EMPTY = "empty"
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class BusinessProfile:
    business_name: str = ""
    address: str = ""
    phone: str = ""
    secondary_phone: str = ""
    email: str = ""
    website: str = ""
    registration_number: str = ""
    footer_message: str = ""
    logo_reference: str = ""
    version_number: int = 0

    def normalized(self) -> BusinessProfile:
        values = {
            field.name: getattr(self, field.name).strip()
            for field in fields(self)
            if isinstance(getattr(self, field.name), str)
        }
        return replace(self, **values)

    def text_values(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in PROFILE_FIELDS}


@dataclass(frozen=True, slots=True)
class ProfileVersion:
    version_number: int
    business_name: str
    address: str
    phone: str
    secondary_phone: str
    email: str
    website: str
    registration_number: str
    footer_message: str
    logo_reference: str
    created_at: str
    updated_at: str

    def to_profile(self) -> BusinessProfile:
        return BusinessProfile(
            business_name=self.business_name,
            address=self.address,
            phone=self.phone,
            secondary_phone=self.secondary_phone,
            email=self.email,
            website=self.website,
            registration_number=self.registration_number,
            footer_message=self.footer_message,
            logo_reference=self.logo_reference,
            version_number=self.version_number,
        )


@dataclass(frozen=True, slots=True)
class ProfileValidation:
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True, slots=True)
class ProfileCompletion:
    status: ProfileStatus
    missing_fields: tuple[str, ...]

    @property
    def label(self) -> str:
        if self.status is ProfileStatus.EMPTY:
            return "No business profile yet"
        if self.status is ProfileStatus.INCOMPLETE:
            missing = ", ".join(FIELD_LABELS[name] for name in self.missing_fields)
            return f"Incomplete - missing: {missing}"
        return "Complete"


def validate_profile(profile: BusinessProfile) -> ProfileValidation:
    normalized = profile.normalized()
    errors: dict[str, str] = {}
    for name in MANDATORY_TEXT_FIELDS:
        if not getattr(normalized, name):
            errors[name] = f"{FIELD_LABELS[name]} is required."
    if not normalized.logo_reference:
        errors["logo"] = "A business logo is required."
    return ProfileValidation(errors=errors)


def assess_completion(profile: BusinessProfile | None) -> ProfileCompletion:
    if profile is None:
        missing: tuple[str, ...] = MANDATORY_TEXT_FIELDS + ("logo",)
        return ProfileCompletion(status=ProfileStatus.EMPTY, missing_fields=missing)
    validation = validate_profile(profile)
    if validation.is_valid:
        return ProfileCompletion(status=ProfileStatus.COMPLETE, missing_fields=())
    missing = tuple(name for name in (*MANDATORY_TEXT_FIELDS, "logo") if name in validation.errors)
    return ProfileCompletion(status=ProfileStatus.INCOMPLETE, missing_fields=missing)


__all__ = [
    "FIELD_LABELS",
    "MANDATORY_TEXT_FIELDS",
    "OPTIONAL_FIELDS",
    "PROFILE_FIELDS",
    "SINGLE_PROFILE_ID",
    "BusinessProfile",
    "ProfileCompletion",
    "ProfileStatus",
    "ProfileValidation",
    "ProfileVersion",
    "assess_completion",
    "validate_profile",
]
