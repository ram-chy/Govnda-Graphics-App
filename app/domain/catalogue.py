"""Product and Service catalogue domain rules.

Phase 10 scope: basic catalogue master data for products and services.
No inventory/stock, variants, barcodes, multiple price lists, tax,
discounts/commissions, transactions, invoices, payments, or accounting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_NAME_LENGTH = 200
MAX_UNIT_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500


class CatalogueKind(StrEnum):
    PRODUCT = "product"
    SERVICE = "service"

    @property
    def label(self) -> str:
        return "Product" if self is CatalogueKind.PRODUCT else "Service"


class CatalogueAuditEventType(StrEnum):
    CREATED = "catalogue.created"
    UPDATED = "catalogue.updated"
    ACTIVATED = "catalogue.activated"
    DEACTIVATED = "catalogue.deactivated"


CATALOGUE_ENTITY_TYPE = "catalogue"


def normalize_catalogue_name(name: str) -> str:
    return " ".join(name.strip().split())


def catalogue_name_key(name: str) -> str:
    return normalize_catalogue_name(name).casefold()


def normalize_optional(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())


@dataclass(frozen=True, slots=True)
class CatalogueItem:
    item_id: int | None
    kind: CatalogueKind
    name: str
    description: str = ""
    unit: str = ""
    default_sale_price_minor: int | None = None
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    @property
    def name_key(self) -> str:
        return catalogue_name_key(self.name)

    def normalized(self) -> CatalogueItem:
        price = self.default_sale_price_minor
        if price is not None:
            price = int(price)
        return CatalogueItem(
            item_id=self.item_id,
            kind=self.kind,
            name=normalize_catalogue_name(self.name),
            description=normalize_optional(self.description),
            unit=normalize_optional(self.unit),
            default_sale_price_minor=price,
            is_active=bool(self.is_active),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(frozen=True, slots=True)
class CatalogueValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogueDuplicateWarning:
    reason: str
    existing_id: int
    existing_name: str


def validate_catalogue_item(item: CatalogueItem) -> CatalogueValidationResult:
    p = item.normalized()
    errors: list[str] = []
    if not p.name:
        errors.append("Name is required.")
    if len(p.name) > MAX_NAME_LENGTH:
        errors.append(f"Name must be at most {MAX_NAME_LENGTH} characters.")
    if len(p.unit) > MAX_UNIT_LENGTH:
        errors.append(f"Unit must be at most {MAX_UNIT_LENGTH} characters.")
    if len(p.description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"Description must be at most {MAX_DESCRIPTION_LENGTH} characters."
        )
    price = p.default_sale_price_minor
    if price is not None:
        if not isinstance(price, int) or isinstance(price, bool):
            errors.append("Default sale price must be an integer amount in paise.")
        elif price < 0:
            errors.append("Default sale price cannot be negative.")
    return CatalogueValidationResult(valid=not errors, errors=tuple(errors))


__all__ = [
    "CATALOGUE_ENTITY_TYPE",
    "CatalogueAuditEventType",
    "CatalogueDuplicateWarning",
    "CatalogueItem",
    "CatalogueKind",
    "CatalogueValidationResult",
    "MAX_DESCRIPTION_LENGTH",
    "MAX_NAME_LENGTH",
    "MAX_UNIT_LENGTH",
    "catalogue_name_key",
    "normalize_catalogue_name",
    "normalize_optional",
    "validate_catalogue_item",
]
