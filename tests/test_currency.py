"""Currency value object tests."""

from __future__ import annotations

import pytest

from app.domain.value_objects.currency import INR, Currency


def test_default_inr_descriptor() -> None:
    assert INR.code == "INR"
    assert INR.symbol == "\u20b9"
    assert INR.decimal_places == 2
    assert INR.grouping == "indian"


def test_currency_is_immutable_and_equatable() -> None:
    other = Currency("INR", "\u20b9", 2, "indian")
    assert other == INR
    with pytest.raises(AttributeError):
        INR.code = "USD"  # type: ignore[misc]


@pytest.mark.parametrize("code", ["inr", "IN", "INRR", "", "I1R", None, 123])
def test_invalid_code_is_rejected(code: object) -> None:
    with pytest.raises(ValueError):
        Currency(code=code, symbol="\u20b9")  # type: ignore[arg-type]


@pytest.mark.parametrize("symbol", ["", "   ", None, 5])
def test_invalid_symbol_is_rejected(symbol: object) -> None:
    with pytest.raises(ValueError):
        Currency(code="INR", symbol=symbol)  # type: ignore[arg-type]


@pytest.mark.parametrize("places", [-1, 5, 2.5, "2", True, None])
def test_invalid_decimal_places_are_rejected(places: object) -> None:
    with pytest.raises(ValueError):
        Currency(code="INR", symbol="\u20b9", decimal_places=places)  # type: ignore[arg-type]


def test_invalid_grouping_is_rejected() -> None:
    with pytest.raises(ValueError):
        Currency(code="INR", symbol="\u20b9", grouping="european")  # type: ignore[arg-type]
