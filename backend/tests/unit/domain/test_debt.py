from datetime import date
from decimal import Decimal

import pytest

from app.domain.allocation import Allocation, allocate_equally
from app.domain.debt import Debt, calculate_debts, calculate_expense_debts
from app.domain.group import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


def test_creates_debts_for_expense_receivers() -> None:
    payer = Member("A", "A")
    receiver_b = Member("B", "B")
    receiver_c = Member("C", "C")
    expense_amount = Money(Decimal("10"), "EUR")
    expense = Expense(
        "expense",
        expense_amount,
        payer,
        date.today(),
        Category("Other"),
        tuple(allocate_equally(expense_amount, [receiver_b, receiver_c])),
    )

    debts = calculate_expense_debts(expense)

    assert debts == [
        Debt(Money(Decimal("5"), "EUR"), receiver_b, payer),
        Debt(Money(Decimal("5"), "EUR"), receiver_c, payer),
    ]


def test_skips_debt_for_payer_allocation() -> None:
    payer = Member("A", "A")
    expense_amount = Money(Decimal("10"), "EUR")
    expense = Expense(
        "expense",
        expense_amount,
        payer,
        date.today(),
        Category("Other"),
        tuple(allocate_equally(expense_amount, [payer])),
    )

    debts = calculate_expense_debts(expense)

    assert debts == []


def create_expense(
    payer: Member,
    receiver: Member,
    amount: str,
    expense_id: str = "expense",
) -> Expense:
    money = Money(Decimal(amount), "EUR")
    allocation = Allocation(receiver, money)
    return Expense(
        expense_id,
        money,
        payer,
        date.today(),
        Category("Other"),
        (allocation,),
    )


def test_adds_debts_in_same_direction() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    debt = Debt(Money(Decimal("3"), "EUR"), member_a, member_b)
    other_debt = Debt(Money(Decimal("2"), "EUR"), member_a, member_b)

    assert debt + other_debt == Debt(Money(Decimal("5"), "EUR"), member_a, member_b)


def test_rejects_adding_debts_in_different_directions() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    debt = Debt(Money(Decimal("3"), "EUR"), member_a, member_b)
    other_debt = Debt(Money(Decimal("2"), "EUR"), member_b, member_a)

    with pytest.raises(ValueError, match="same direction"):
        debt + other_debt


def test_combines_debts_in_same_direction() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    expenses = [
        create_expense(member_a, member_b, "3.0005"),
        create_expense(member_a, member_b, "2.0005"),
    ]

    debts = calculate_debts(expenses)

    assert debts == [Debt(Money(Decimal("5.0010"), "EUR"), member_b, member_a)]


def test_reduces_debt_with_smaller_opposite_expense() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    expenses = [
        create_expense(member_a, member_b, "5"),
        create_expense(member_b, member_a, "4"),
    ]

    debts = calculate_debts(expenses)

    assert debts == [Debt(Money(Decimal("1"), "EUR"), member_b, member_a)]


def test_removes_debt_with_equal_opposite_expense() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    expenses = [
        create_expense(member_a, member_b, "5"),
        create_expense(member_b, member_a, "5"),
    ]

    debts = calculate_debts(expenses)

    assert debts == []


def test_reverses_debt_with_larger_opposite_expense() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    expenses = [
        create_expense(member_a, member_b, "3"),
        create_expense(member_b, member_a, "5"),
    ]

    debts = calculate_debts(expenses)

    assert debts == [Debt(Money(Decimal("2"), "EUR"), member_a, member_b)]
