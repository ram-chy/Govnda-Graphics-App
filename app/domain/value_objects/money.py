"""INR money value object and integer-paise conversion.

Phase 2 stores no monetary columns yet, but every future accounting and
inventory module must use this module at the persistence boundary:

* Domain calculations use :class:`decimal.Decimal`, never ``float``.
* Persistence uses signed 64-bit integer paise (1 rupee = 100 paise).
* Conversion rounds explicitly with ``ROUND_HALF_UP`` or rejects any value that
  is not exactly representable (``decimal_to_minor_exact``).
* Negative amounts are allowed for credit/adjustment flows; callers that cannot
  accept them pass ``allow_negative=False``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

INR_MINOR_UNIT = 2
PAISE_PER_RUPEE = 100

# SQLite stores integers as signed 64-bit values.
MIN_MINOR = -(2**63)
MAX_MINOR = 2**63 - 1

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")

type DecimalLike = Decimal | int | str


class MoneyError(ValueError):
    """Base class for monetary conversion failures."""


class MoneyPrecisionError(MoneyError):
    """The value cannot be represented exactly at the required scale."""


class MoneyRangeError(MoneyError):
    """The value exceeds the signed 64-bit paise range or violates a sign rule."""


def _to_decimal(amount: DecimalLike) -> Decimal:
    if isinstance(amount, bool):
        raise TypeError("boolean values are not valid monetary amounts")
    if isinstance(amount, Decimal):
        value = amount
    elif isinstance(amount, int):
        value = Decimal(amount)
    elif isinstance(amount, str):
        text = amount.strip()
        if not text:
            raise ValueError("monetary amount must not be empty")
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"invalid monetary amount: {amount!r}") from exc
    else:
        raise TypeError(
            "monetary amount must be a Decimal, int, or numeric string; float is not allowed"
        )
    if not value.is_finite():
        raise ValueError("monetary amount must be finite")
    return value


def _quantum(decimal_places: int) -> Decimal:
    if isinstance(decimal_places, bool) or not isinstance(decimal_places, int):
        raise TypeError("decimal_places must be an integer")
    if not 0 <= decimal_places <= 8:
        raise ValueError("decimal_places must be between 0 and 8")
    return Decimal(1).scaleb(-decimal_places)


def _check_range(minor: int) -> int:
    if not MIN_MINOR <= minor <= MAX_MINOR:
        raise MoneyRangeError(
            f"amount is outside the supported paise range ({MIN_MINOR}..{MAX_MINOR})"
        )
    return minor


def decimal_to_minor(
    amount: DecimalLike,
    *,
    decimal_places: int = INR_MINOR_UNIT,
    allow_negative: bool = True,
) -> int:
    """Convert an exact amount to integer minor units using ``ROUND_HALF_UP``.

    This is the conversion for computed values that are allowed to round once at
    a defined boundary. Use :func:`decimal_to_minor_exact` for raw input where
    unexpected precision must be rejected instead of rounded.
    """
    value = _to_decimal(amount)
    if value < 0 and not allow_negative:
        raise MoneyRangeError("negative amounts are not allowed in this context")
    try:
        scaled = value.quantize(_quantum(decimal_places), rounding=ROUND_HALF_UP)
        minor = int(scaled.scaleb(decimal_places))
    except (InvalidOperation, OverflowError) as exc:
        raise MoneyRangeError(f"monetary amount is outside the supported range: {value}") from exc
    return _check_range(minor)


def decimal_to_minor_exact(
    amount: DecimalLike,
    *,
    decimal_places: int = INR_MINOR_UNIT,
    allow_negative: bool = True,
) -> int:
    """Convert without rounding; reject values with unsupported precision."""
    value = _to_decimal(amount)
    if value < 0 and not allow_negative:
        raise MoneyRangeError("negative amounts are not allowed in this context")
    try:
        scaled = value.quantize(_quantum(decimal_places))
    except InvalidOperation as exc:
        raise MoneyRangeError(f"monetary amount is outside the supported range: {value}") from exc
    if scaled != value:
        raise MoneyPrecisionError(
            f"amount {value} cannot be represented exactly with {decimal_places} decimal places"
        )
    return _check_range(int(scaled.scaleb(decimal_places)))


def minor_to_decimal(minor: int, *, decimal_places: int = INR_MINOR_UNIT) -> Decimal:
    """Convert integer minor units back to an exact ``Decimal``."""
    if isinstance(minor, bool) or not isinstance(minor, int):
        raise TypeError("minor units must be an integer")
    _check_range(minor)
    return Decimal(minor).scaleb(-decimal_places)


@dataclass(frozen=True, slots=True)
class Money:
    """An exact INR amount stored as integer paise."""

    minor: int
    currency: str = "INR"

    def __post_init__(self) -> None:
        if isinstance(self.minor, bool) or not isinstance(self.minor, int):
            raise TypeError("minor units must be an integer")
        _check_range(self.minor)
        if not isinstance(self.currency, str) or not _CURRENCY_CODE_PATTERN.match(self.currency):
            raise ValueError("currency must be a three-letter ISO 4217 code")

    @classmethod
    def from_decimal(
        cls,
        amount: DecimalLike,
        *,
        currency: str = "INR",
        allow_negative: bool = True,
    ) -> Money:
        return cls(
            minor=decimal_to_minor(amount, allow_negative=allow_negative),
            currency=currency,
        )

    @classmethod
    def from_minor(cls, minor: int, *, currency: str = "INR") -> Money:
        return cls(minor=minor, currency=currency)

    def to_decimal(self) -> Decimal:
        return minor_to_decimal(self.minor)

    def __str__(self) -> str:
        return f"{self.to_decimal()} {self.currency}"


__all__ = [
    "INR_MINOR_UNIT",
    "MAX_MINOR",
    "MIN_MINOR",
    "Money",
    "MoneyError",
    "MoneyPrecisionError",
    "MoneyRangeError",
    "PAISE_PER_RUPEE",
    "decimal_to_minor",
    "decimal_to_minor_exact",
    "minor_to_decimal",
]
