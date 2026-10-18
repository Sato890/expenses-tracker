from decimal import Context, Decimal, localcontext

import pytest

from app.domain.money import Money


def test_adds_money_with_calculation_precision() -> None:
    value1 = Money(Decimal("333333333333333333.333333333333333334"), "EUR")
    value2 = Money(Decimal("0.000000000000000001"), "EUR")

    with localcontext(Context(prec=2)):
        result = value1 + value2

    assert result == Money(Decimal("333333333333333333.333333333333333335"), "EUR")


def test_rejects_unsupported_operands() -> None:
    money = Money(Decimal("5"), "EUR")

    with pytest.raises(TypeError):
        money + 5

    with pytest.raises(TypeError):
        money - 5

    with pytest.raises(TypeError):
        _ = money < 5

    with pytest.raises(TypeError):
        money * money

    with pytest.raises(TypeError):
        money / money


def test_subtracts_money_with_calculation_precision() -> None:
    value1 = Money(Decimal("333333333333333333.333333333333333334"), "EUR")
    value2 = Money(Decimal("0.000000000000000001"), "EUR")

    with localcontext(Context(prec=2)):
        result = value1 - value2

    assert result == Money(Decimal("333333333333333333.333333333333333333"), "EUR")


def test_negates_money_without_rounding() -> None:
    money = Money(Decimal("-333333333333333333.333333333333333334"), "EUR")

    with localcontext(Context(prec=2)):
        result = -money

    assert result == Money(Decimal("333333333333333333.333333333333333334"), "EUR")


def test_divides_money_with_calculation_precision() -> None:
    money = Money(Decimal("999999999999999998"), "EUR")

    with localcontext(Context(prec=2)):
        result = money / 3

    assert result == Money(Decimal("333333333333333332.6666666666666666667"), "EUR")


def test_multiplies_money_with_calculation_precision() -> None:
    money = Money(Decimal("333333333333333332.666666666666666666"), "EUR")

    with localcontext(Context(prec=2)):
        result = money * 3

    assert result == Money(Decimal("999999999999999997.999999999999999998"), "EUR")


def test_rounds_money_down_to_the_requested_unit() -> None:
    money = Money(Decimal("10.009"), "EUR")

    with localcontext(Context(prec=2)):
        result = money.round_down_to(Decimal("0.01"))

    assert result == Money(Decimal("10.00"), "EUR")
