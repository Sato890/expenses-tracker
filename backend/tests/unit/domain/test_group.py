from datetime import date
from decimal import Decimal

import pytest

from app.domain.allocation import Allocation
from app.domain.debt import Debt
from app.domain.group import Group, Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


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


def test_derives_debts_from_current_transactions() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", members=[member_a, member_b])
    group.add_expense(create_expense(member_a, member_b, "5", "expense-a"))

    assert group.debts == [Debt(Money(Decimal("5"), "EUR"), member_b, member_a)]

    group.add_expense(create_expense(member_b, member_a, "4", "expense-b"))

    assert group.debts == [Debt(Money(Decimal("1"), "EUR"), member_b, member_a)]


def test_calculates_settlement_amounts_for_every_member() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    member_d = Member("D", "D")

    group = Group("group", "Group", members=[member_a, member_b, member_c, member_d])
    group.add_expense(create_expense(member_a, member_b, "3.0005", "expense-a"))
    group.add_expense(create_expense(member_c, member_a, "2.0005", "expense-b"))

    settlement_amounts = group.calculate_member_settlement_amounts()

    assert settlement_amounts == {
        member_a: Decimal("1.0000"),
        member_b: Decimal("-3.0005"),
        member_c: Decimal("2.0005"),
        member_d: Decimal("0"),
    }
    assert sum(settlement_amounts.values()) == Decimal("0")


def test_adds_valid_expense() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer, receiver])
    expense = create_expense(payer, receiver, "5")

    group.add_expense(expense)

    assert group.transactions == (expense,)


def test_rejects_expense_from_non_member_payer() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[receiver])

    with pytest.raises(ValueError, match="Payer is not in the group"):
        group.add_expense(create_expense(payer, receiver, "5"))

    assert group.transactions == ()


def test_rejects_expense_for_non_member_receiver() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer])

    with pytest.raises(ValueError, match="Receiver is not in the group"):
        group.add_expense(create_expense(payer, receiver, "5"))

    assert group.transactions == ()


def test_rejects_expense_with_invalid_allocations() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer, receiver])
    expense = Expense(
        "expense",
        Money(Decimal("5"), "EUR"),
        payer,
        date.today(),
        Category("Other"),
        (Allocation(receiver, Money(Decimal("4"), "EUR")),),
    )

    with pytest.raises(ValueError, match="allocations must add up"):
        group.add_expense(expense)

    assert group.transactions == ()


def test_rejects_duplicate_expense_id() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer, receiver])
    expense = create_expense(payer, receiver, "5", "expense")
    duplicate = create_expense(payer, receiver, "4", "expense")
    group.add_expense(expense)

    with pytest.raises(ValueError, match="Expense ID already exists"):
        group.add_expense(duplicate)

    assert group.transactions == (expense,)


def test_removes_expense_by_id() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer, receiver])
    expense_a = create_expense(payer, receiver, "5", "expense-a")
    expense_b = create_expense(payer, receiver, "5", "expense-b")
    group.add_expense(expense_a)
    group.add_expense(expense_b)

    group.remove_expense("expense-a")

    assert group.transactions == (expense_b,)


def test_edits_expense_by_id() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", members=[member_a, member_b])
    original = create_expense(member_a, member_b, "5", "expense")
    replacement = create_expense(member_b, member_a, "4", "expense")
    group.add_expense(original)

    group.edit_expense(replacement)

    assert group.transactions == (replacement,)
    assert group.debts == [Debt(Money(Decimal("4"), "EUR"), member_a, member_b)]


def test_rejects_invalid_expense_edit_without_changing_transactions() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer, receiver])
    original = create_expense(payer, receiver, "5", "expense")
    replacement = Expense(
        "expense",
        Money(Decimal("5"), "EUR"),
        payer,
        date.today(),
        Category("Other"),
        (Allocation(receiver, Money(Decimal("4"), "EUR")),),
    )
    group.add_expense(original)

    with pytest.raises(ValueError, match="allocations must add up"):
        group.edit_expense(replacement)

    assert group.transactions == (original,)
