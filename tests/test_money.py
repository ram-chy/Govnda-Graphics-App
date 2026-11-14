"""Integer-paise money conversion and the INR money value object."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.value_objects.money import (
    MAX_MINOR,
    MIN_MINOR,
    Money,
    MoneyPrecisionError,
    MoneyRangeError,
    decimal_to_minor,
    decimal_to_minor_exact,
    minor_to_decimal,
)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("0"), 0),
        (Decimal("0.01"), 1),
        (Decimal("1"), 100),
        (Decimal("123.45"), 12345),
        ("123.45", 12345),
        (123, 12300),
        (Decimal("99999999.99"), 9_999_999_999),
    ],
)
def test_decimal_to_minor_converts_exactly(amount: object, expected: int) -> None:
    assert decimal_to_minor(amount) == expected  # type: ignore[arg-type]


def test_decimal_to_minor_rounds_half_up_once() -> None:
    assert decimal_to_minor(Decimal("0.004")) == 0
    assert decimal_to_minor(Decimal("0.005")) == 1
    assert decimal_to_minor(Decimal("1.005")) == 101
    assert decimal_to_minor(Decimal("-1.005")) == -101


def test_decimal_to_minor_rejects_float() -> None:
    with pytest.raises(TypeError):
        decimal_to_minor(1.25)  # type: ignore[arg-type]


def test_decimal_to_minor_rejects_bool() -> None:
    with pytest.raises(TypeError):
        decimal_to_minor(True)  # type: ignore[arg-type]


def test_decimal_to_minor_rejects_nan_and_infinity() -> None:
    with pytest.raises(ValueError):
        decimal_to_minor(Decimal("NaN"))
    with pytest.raises(ValueError):
        decimal_to_minor(Decimal("Infinity"))


def test_decimal_to_minor_can_reject_negative_amounts() -> None:
    with pytest.raises(MoneyRangeError):
        decimal_to_minor(Decimal("-0.01"), allow_negative=False)


def test_exact_conversion_rejects_unexpected_precision() -> None:
    with pytest.raises(MoneyPrecisionError):
        decimal_to_minor_exact(Decimal("1.234"))


def test_exact_conversion_accepts_representable_values() -> None:
    assert decimal_to_minor_exact("1.23") == 123
    assert decimal_to_minor_exact("1.2") == 120
    assert decimal_to_minor_exact("1") == 100


def test_conversion_enforces_signed_64_bit_range() -> None:
    with pytest.raises(MoneyRangeError):
        decimal_to_minor(Decimal(MAX_MINOR))
    with pytest.raises(MoneyRangeError):
        decimal_to_minor(Decimal(MIN_MINOR))
    assert decimal_to_minor(Decimal(MAX_MINOR).scaleb(-2)) == MAX_MINOR
    assert decimal_to_minor(Decimal(MIN_MINOR).scaleb(-2)) == MIN_MINOR


def test_minor_to_decimal_is_exact() -> None:
    assert minor_to_decimal(12345) == Decimal("123.45")
    assert minor_to_decimal(-1) == Decimal("-0.01")
    assert isinstance(minor_to_decimal(1), Decimal)


def test_minor_to_decimal_rejects_non_integer() -> None:
    with pytest.raises(TypeError):
        minor_to_decimal("100")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        minor_to_decimal(True)  # type: ignore[arg-type]


def test_money_round_trips_between_decimal_and_paise() -> None:
    money = Money.from_decimal("125000.50")

    assert money.minor == 12_500_050
    assert money.currency == "INR"
    assert money.to_decimal() == Decimal("125000.50")
    assert str(money) == "125000.50 INR"


def test_money_from_minor_and_range_checks() -> None:
    assert Money.from_minor(MAX_MINOR).minor == MAX_MINOR
    with pytest.raises(MoneyRangeError):
        Money.from_minor(MAX_MINOR + 1)


def test_money_rejects_invalid_currency() -> None:
    with pytest.raises(ValueError):
        Money(minor=1, currency="rupee")
    with pytest.raises(ValueError):
        Money(minor=1, currency="INR2")


def test_money_can_reject_negative_values() -> None:
    with pytest.raises(MoneyRangeError):
        Money.from_decimal("-1.00", allow_negative=False)
