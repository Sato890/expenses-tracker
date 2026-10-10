from datetime import date
from decimal import Decimal

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
