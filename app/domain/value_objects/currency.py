"""Currency value object and the application's default currency."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

CurrencyGrouping = Literal["indian", "western"]

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")
_VALID_GROUPING: tuple[str, ...] = ("indian", "western")


@dataclass(frozen=True, slots=True)
class Currency:
    """Immutable descriptor for a currency's display rules.

    This object carries presentation data only. Monetary calculation rules
    (rounding policy, storage scale) live in the money value objects added in a
    later phase.
    """

    code: str
    symbol: str
    decimal_places: int = 2
    grouping: CurrencyGrouping = "indian"

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not _CURRENCY_CODE_PATTERN.match(self.code):
            raise ValueError("currency code must be a three-letter ISO 4217 code")
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("currency symbol must not be empty")
        if (
            isinstance(self.decimal_places, bool)
            or not isinstance(self.decimal_places, int)
            or not 0 <= self.decimal_places <= 4
        ):
            raise ValueError("decimal_places must be an integer from 0 to 4")
        if self.grouping not in _VALID_GROUPING:
            raise ValueError("grouping must be 'indian' or 'western'")


INR = Currency(
    code="INR",
    symbol="\u20b9",
    decimal_places=2,
    grouping="indian",
)
