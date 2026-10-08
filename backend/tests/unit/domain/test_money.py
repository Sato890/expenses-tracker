from decimal import Decimal

import pytest

from app.domain.money import Money


def test_add_money_to_money() -> None:
    value1 = Money(Decimal("5"), "EUR")
    value2 = Money(Decimal("5"), "EUR")

    assert value1 + value2 == Money(Decimal("10"), "EUR")


def test_add_money_to_other() -> None:
    with pytest.raises(NotImplementedError):
        Money(Decimal("5"), "EUR") + 5
