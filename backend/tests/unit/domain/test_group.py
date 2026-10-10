from datetime import date
from decimal import Decimal

import pytest

from app.domain.allocation import Allocation
from app.domain.debt import Debt
from app.domain.group import Group, Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


def create_expense(payer: Member, receiver: Member, amount: str) -> Expense:
    money = Money(Decimal(amount), "EUR")
    allocation = Allocation(receiver, money)
    return Expense(money, payer, date.today(), Category("Other"), (allocation,))


def test_derives_debts_from_current_transactions() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", members=[member_a, member_b])
    group.transactions.append(create_expense(member_a, member_b, "5"))

    assert group.debts == [Debt(Money(Decimal("5"), "EUR"), member_b, member_a)]

    group.transactions.append(create_expense(member_b, member_a, "4"))

    assert group.debts == [Debt(Money(Decimal("1"), "EUR"), member_b, member_a)]


def test_calculates_settlement_amounts_for_every_member() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    member_d = Member("D", "D")

    group = Group(
        "group",
        "Group",
        members=[member_a, member_b, member_c, member_d],
        transactions=[
            create_expense(member_a, member_b, "3.0005"),
            create_expense(member_c, member_a, "2.0005"),
        ],
    )

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

    assert group.transactions == [expense]


def test_rejects_expense_from_non_member_payer() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[receiver])

    with pytest.raises(ValueError, match="Payer is not in the group"):
        group.add_expense(create_expense(payer, receiver, "5"))

    assert group.transactions == []


def test_rejects_expense_for_non_member_receiver() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer])

    with pytest.raises(ValueError, match="Receiver is not in the group"):
        group.add_expense(create_expense(payer, receiver, "5"))

    assert group.transactions == []


def test_rejects_expense_with_invalid_allocations() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", members=[payer, receiver])
    expense = Expense(
        Money(Decimal("5"), "EUR"),
        payer,
        date.today(),
        Category("Other"),
        (Allocation(receiver, Money(Decimal("4"), "EUR")),),
    )

    with pytest.raises(ValueError, match="allocations must add up"):
        group.add_expense(expense)

    assert group.transactions == []
