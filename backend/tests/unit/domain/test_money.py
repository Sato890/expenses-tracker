from decimal import Decimal

import pytest

from app.domain.money import Money


def test_add_money_to_money() -> None:
    value1 = Money(Decimal("5"), "EUR")
    value2 = Money(Decimal("5"), "EUR")

    assert value1 + value2 == Money(Decimal("10"), "EUR")


def test_rejects_unsupported_operands() -> None:
    money = Money(Decimal("5"), "EUR")

    with pytest.raises(TypeError):
        money + 5

    with pytest.raises(TypeError):
        money - 5


def test_subtract_money_from_money() -> None:
    value1 = Money(Decimal("8"), "EUR")
    value2 = Money(Decimal("3"), "EUR")

    assert value1 - value2 == Money(Decimal("5"), "EUR")
