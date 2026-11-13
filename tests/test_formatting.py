"""INR and generic currency formatting tests."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.formatting import format_money
from app.domain.value_objects.currency import INR, Currency

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("0"), "\u20b90.00"),
        (Decimal("0.00"), "\u20b90.00"),
        (Decimal("1"), "\u20b91.00"),
        (Decimal("999.99"), "\u20b9999.99"),
        (Decimal("1000"), "\u20b91,000.00"),
        (Decimal("1250.50"), "\u20b91,250.50"),
        (Decimal("9999.99"), "\u20b99,999.99"),
        (Decimal("10000"), "\u20b910,000.00"),
        (Decimal("99999.99"), "\u20b999,999.99"),
        (Decimal("100000"), "\u20b91,00,000.00"),
        (Decimal("125000.50"), "\u20b91,25,000.50"),
        (Decimal("1000000.00"), "\u20b910,00,000.00"),
        (Decimal("12345678.90"), "\u20b91,23,45,678.90"),
        (Decimal("123456789.999"), "\u20b912,34,56,790.00"),
        (Decimal("-1250.50"), "-\u20b91,250.50"),
        (Decimal("-0.004"), "\u20b90.00"),
        (Decimal("-0.005"), "-\u20b90.01"),
        (Decimal("-125000.50"), "-\u20b91,25,000.50"),
    ],
)
def test_inr_formatting(amount: Decimal, expected: str) -> None:
    assert format_money(amount, INR) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("1250.504"), "\u20b91,250.50"),
        (Decimal("1250.505"), "\u20b91,250.51"),
        (Decimal("2.675"), "\u20b92.68"),
        (Decimal("0.005"), "\u20b90.01"),
        (Decimal("0.0049"), "\u20b90.00"),
        (Decimal("999.999"), "\u20b91,000.00"),
    ],
)
def test_rounding_is_half_up_at_two_places(amount: Decimal, expected: str) -> None:
    assert format_money(amount, INR) == expected


def test_integer_and_string_inputs_are_exact() -> None:
    assert format_money(1250, INR) == "\u20b91,250.00"
    assert format_money("1250.50", INR) == "\u20b91,250.50"
    assert format_money("1,25,000.50", INR) == "\u20b91,25,000.50"
    assert format_money("  1250.50  ", INR) == "\u20b91,250.50"


def test_default_currency_is_inr() -> None:
    assert format_money(Decimal("1250.50")) == "\u20b91,250.50"


def test_grouping_can_be_disabled() -> None:
    assert format_money(Decimal("125000.50"), INR, grouping=False) == "\u20b9125000.50"


def test_western_grouping() -> None:
    usd = Currency("USD", "$", 2, "western")
    assert format_money(Decimal("1234567.89"), usd) == "$1,234,567.89"
    assert format_money(Decimal("-125000.50"), usd) == "-$125,000.50"


def test_zero_decimal_currency() -> None:
    jpy = Currency("JPY", "\u00a5", 0, "western")
    assert format_money(Decimal("1234.5"), jpy) == "\u00a51,235"
    assert format_money(Decimal("0"), jpy) == "\u00a50"


@pytest.mark.parametrize("amount", [1250.50, 0.0, -1.5])
def test_float_input_is_rejected(amount: float) -> None:
    with pytest.raises(TypeError):
        format_money(amount, INR)  # type: ignore[arg-type]


@pytest.mark.parametrize("amount", [True, False, None, object(), [], {}])
def test_unsupported_input_types_are_rejected(amount: object) -> None:
    with pytest.raises(TypeError):
        format_money(amount, INR)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "amount",
    [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_non_finite_values_are_rejected(amount: Decimal) -> None:
    with pytest.raises(ValueError):
        format_money(amount, INR)


@pytest.mark.parametrize("amount", ["", "   ", "abc", "1..2", "1e", "\u20b91,250.50"])
def test_invalid_strings_are_rejected(amount: str) -> None:
    with pytest.raises(ValueError):
        format_money(amount, INR)


def test_out_of_range_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        format_money(Decimal("1E+999999"), INR)


def test_currency_must_be_a_currency_instance() -> None:
    with pytest.raises(TypeError):
        format_money(Decimal("1"), "INR")  # type: ignore[arg-type]


def test_formatting_module_never_calls_float() -> None:
    source = (PROJECT_ROOT / "app" / "core" / "formatting.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    float_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
    ]
    assert not float_calls
