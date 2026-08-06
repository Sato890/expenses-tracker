from decimal import Context, Decimal, localcontext

from app.domain.allocation import Allocation, allocate_equally
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
    assert allocations[0].amount == Money(Decimal("15.111111111111111111"), "EUR")
    assert allocations[1].amount == allocations[0].amount


def test_assigns_residual_to_first_receiver() -> None:
    amount = Money(Decimal("30.000000000000000001"), "EUR")
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    receivers = [member_a, member_b]

    allocations = allocate_equally(amount, receivers)

    assert len(allocations) == 2
    assert allocations[0].receiver == member_a
    assert allocations[1].receiver == member_b
    assert allocations[0].amount == Money(Decimal("15.000000000000000001"), "EUR")
    assert allocations[1].amount == Money(Decimal("15.000000000000000000"), "EUR")
    assert allocations[0].amount.currency == amount.currency
    assert allocations[1].amount.currency == amount.currency


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

    assert allocations[0].amount == Money(Decimal("10.195"), "EUR")
    assert allocations[1].amount == Money(Decimal("10.195"), "EUR")
