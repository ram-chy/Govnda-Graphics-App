"""Display formatting for monetary values.

Formatting is deliberately separate from business calculation logic. Callers
pass an exact :class:`~decimal.Decimal` (or an integer or numeric string);
binary floats are rejected so display code cannot become a hidden source of
rounding error.

The default application currency is INR with Indian digit grouping, producing
values such as ``₹1,25,000.50``.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.domain.value_objects.currency import INR, Currency

type MonetaryInput = Decimal | int | str


def _to_decimal(amount: MonetaryInput) -> Decimal:
    """Convert accepted input to an exact Decimal without using float."""
    if isinstance(amount, bool):
        raise TypeError("boolean values are not valid monetary amounts")
    if isinstance(amount, Decimal):
        return amount
    if isinstance(amount, int):
        return Decimal(amount)
    if isinstance(amount, str):
        text = amount.strip().replace(",", "")
        if not text:
            raise ValueError("monetary amount must not be empty")
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"invalid monetary amount: {amount!r}") from exc
    raise TypeError(
        "monetary amount must be a Decimal, int, or numeric string; float is not allowed"
    )


def _group_digits(digits: str, style: str) -> str:
    """Insert separators into an unsigned integer string."""
    if style == "indian":
        if len(digits) <= 3:
            return digits
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        groups.append(tail)
        return ",".join(groups)

    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return ",".join(groups)


def format_money(
    amount: MonetaryInput,
    currency: Currency | None = None,
    *,
    grouping: bool = True,
) -> str:
    """Format ``amount`` for display using ``currency``.

    Args:
        amount: Exact amount as ``Decimal``, ``int``, or numeric string.
        currency: Display rules. Defaults to INR when omitted.
        grouping: When false, digit separators are not inserted.

    Raises:
        TypeError: If the amount is a float, boolean, or unsupported type.
        ValueError: If the amount is not finite, not numeric, or outside the
            range the Decimal context can quantize.
    """
    if currency is None:
        currency = INR
    if not isinstance(currency, Currency):
        raise TypeError("currency must be a Currency instance")

    value = _to_decimal(amount)
    if not value.is_finite():
        raise ValueError("monetary amount must be finite")

    quantum = Decimal(1).scaleb(-currency.decimal_places)
    try:
        rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"monetary amount is outside the supported range: {value}") from exc

    sign = "-" if rounded < 0 else ""
    text = f"{abs(rounded):.{currency.decimal_places}f}"
    integer_text, separator, fraction_text = text.partition(".")

    if grouping:
        integer_text = _group_digits(integer_text, currency.grouping)

    formatted_fraction = f"{separator}{fraction_text}" if separator else ""
    return f"{sign}{currency.symbol}{integer_text}{formatted_fraction}"
