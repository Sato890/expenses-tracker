from decimal import Context, Decimal, localcontext

import pytest

from app.domain.allocation import (
    Allocation,
    allocate_equally,
    validate_exact_allocations,
)
from app.domain.group import Member
from app.domain.money import Money


def test_allocates_divisible_amount_equally() -> None:
    amount = Money(Decimal("30.222222222222222222"), "EUR")
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    receivers = [member_a, member_b]

    allocations = allocate_equally(amount, receivers)

    assert len(allocations) == 2
    assert allocations[0].receiver == member_a
    assert allocations[1].receiver == member_b
    assert allocations[0].share == Money(Decimal("15.111111111111111111"), "EUR")
    assert allocations[1].share == allocations[0].share


def test_assigns_residual_to_first_receiver() -> None:
    amount = Money(Decimal("30.000000000000000001"), "EUR")
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    receivers = [member_a, member_b]

    allocations = allocate_equally(amount, receivers)

    assert len(allocations) == 2
    assert allocations[0].receiver == member_a
    assert allocations[1].receiver == member_b
    assert allocations[0].share == Money(Decimal("15.000000000000000001"), "EUR")
    assert allocations[1].share == Money(Decimal("15.000000000000000000"), "EUR")
    assert allocations[0].share.currency == amount.currency
    assert allocations[1].share.currency == amount.currency


def test_assigns_calculation_residual_in_receiver_order() -> None:
    amount = Money(Decimal("10"), "EUR")
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    receivers = [member_a, member_b, member_c]

    allocations = allocate_equally(amount, receivers)

    assert allocations == [
        Allocation(member_a, Money(Decimal("3.333333333333333334"), "EUR")),
        Allocation(member_b, Money(Decimal("3.333333333333333333"), "EUR")),
        Allocation(member_c, Money(Decimal("3.333333333333333333"), "EUR")),
    ]


def test_ignores_ambient_decimal_context() -> None:
    amount = Money(Decimal("20.39"), "EUR")
    member_a = Member("A", "A")
    member_b = Member("B", "B")

    context = Context(prec=2)

    with localcontext(context):
        allocations = allocate_equally(amount, [member_a, member_b])

    assert allocations[0].share == Money(Decimal("10.195"), "EUR")
    assert allocations[1].share == Money(Decimal("10.195"), "EUR")


def test_accepts_sub_cent_exact_allocations() -> None:
    allocation_a = Allocation(Member("A", "A"), Money(Decimal("6.0025"), "EUR"))
    allocation_b = Allocation(Member("B", "B"), Money(Decimal("4.0025"), "EUR"))

    validate_exact_allocations(
        Money(Decimal("10.005"), "EUR"), [allocation_a, allocation_b]
    )


def test_rejects_allocation_total_that_does_not_match_expense() -> None:
    allocation_a = Allocation(Member("A", "A"), Money(Decimal("3.0005"), "EUR"))
    allocation_b = Allocation(Member("B", "B"), Money(Decimal("3"), "EUR"))

    with pytest.raises(ValueError, match="The allocations must add up to the total"):
        validate_exact_allocations(
            Money(Decimal("6"), "EUR"), [allocation_a, allocation_b]
        )


def test_requires_positive_expense_amount() -> None:
    allocation = Allocation(Member("A", "A"), Money(Decimal("1"), "EUR"))

    with pytest.raises(ValueError, match="The expense amount must be positive"):
        validate_exact_allocations(Money(Decimal("0"), "EUR"), [allocation])


def test_requires_allocations() -> None:
    with pytest.raises(ValueError, match="At least one allocation is required"):
        validate_exact_allocations(Money(Decimal("10"), "EUR"), [])


def test_requires_positive_allocation_shares() -> None:
    allocation_a = Allocation(Member("A", "A"), Money(Decimal("0"), "EUR"))
    allocation_b = Allocation(Member("B", "B"), Money(Decimal("10"), "EUR"))

    with pytest.raises(ValueError, match="Allocation shares must be positive"):
        validate_exact_allocations(
            Money(Decimal("10"), "EUR"), [allocation_a, allocation_b]
        )
