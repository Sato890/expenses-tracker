from datetime import date
from decimal import Decimal

from app.domain.allocation import allocate_equally
from app.domain.debt import Debt, calculate_debt_changes
from app.domain.group import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


def test_creates_debt_changes_for_expense_receivers() -> None:
    payer = Member("A", "A")
    receiver_b = Member("B", "B")
    receiver_c = Member("C", "C")
    expense_amount = Money(Decimal("10"), "EUR")
    expense = Expense(
        expense_amount,
        payer,
        date.today(),
        Category("Other"),
        tuple(allocate_equally(expense_amount, [receiver_b, receiver_c])),
    )

    debts = calculate_debt_changes(expense)

    assert debts == [
        Debt(Money(Decimal("5"), "EUR"), receiver_b, payer),
        Debt(Money(Decimal("5"), "EUR"), receiver_c, payer),
    ]


def test_omits_debt_change_for_payer_own_allocation() -> None:
    payer = Member("A", "A")
    expense_amount = Money(Decimal("10"), "EUR")
    expense = Expense(
        expense_amount,
        payer,
        date.today(),
        Category("Other"),
        tuple(allocate_equally(expense_amount, [payer])),
    )

    debts = calculate_debt_changes(expense)

    assert debts == []
