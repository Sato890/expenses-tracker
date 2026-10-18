from datetime import date
from decimal import Decimal

from app.domain.allocation import Allocation
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


def test_normalizes_single_allocation_to_tuple() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    amount = Money(Decimal("10"), "EUR")
    allocation = Allocation(receiver, amount)

    expense = Expense(
        "expense", amount, payer, date(2026, 1, 1), Category("Other"), allocation
    )

    assert expense.allocations == (allocation,)
