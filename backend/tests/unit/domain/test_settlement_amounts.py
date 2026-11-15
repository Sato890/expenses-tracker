from datetime import date
from decimal import Decimal

from app.domain.allocation import Allocation
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.settlement_amounts import calculate_expense_balance_changes
from app.domain.transaction import Category, Expense


def test_calculates_exact_expense_balance_changes_with_own_share() -> None:
    alex = Member("alex", "Alex")
    bea = Member("bea", "Bea")
    expense = Expense(
        "expense",
        Money(Decimal("10.005"), "EUR"),
        alex,
        date(2026, 11, 15),
        Category("Groceries"),
        [
            Allocation(alex, Money(Decimal("5.0025"), "EUR")),
            Allocation(bea, Money(Decimal("5.0025"), "EUR")),
        ],
    )

    assert calculate_expense_balance_changes(expense) == {
        alex: Money(Decimal("5.0025"), "EUR"),
        bea: Money(Decimal("-5.0025"), "EUR"),
    }


def test_self_only_expense_changes_no_balance() -> None:
    alex = Member("alex", "Alex")
    amount = Money(Decimal("0.000000000000000001"), "EUR")
    expense = Expense(
        "expense",
        amount,
        alex,
        date(2026, 11, 15),
        Category("Groceries"),
        Allocation(alex, amount),
    )

    assert calculate_expense_balance_changes(expense) == {}
