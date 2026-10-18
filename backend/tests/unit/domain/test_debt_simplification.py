from datetime import date
from decimal import Decimal

from app.domain.allocation import Allocation
from app.domain.debt import Debt
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


def create_expense(
    *,
    payer: Member,
    receiver: Member,
    amount: str,
    expense_id: str = "expense",
) -> Expense:
    money = Money(Decimal(amount), "EUR")
    return Expense(
        expense_id=expense_id,
        amount=money,
        payer=payer,
        date=date.today(),
        category=Category("Other"),
        allocations=Allocation(receiver, money),
    )


def test_simplifies_circular_debts_to_two_debts() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")

    group = Group("group", "Group", _members=[member_a, member_b, member_c])

    group.add_expense(
        create_expense(
            payer=member_b, receiver=member_a, amount="20.001", expense_id="A"
        )
    )
    group.add_expense(
        create_expense(
            payer=member_c, receiver=member_b, amount="25.002", expense_id="B"
        )
    )
    group.add_expense(
        create_expense(payer=member_a, receiver=member_c, amount="10", expense_id="C")
    )
    original_debts = group.debts
    original_transactions = group.transactions
    assert len(original_debts) == 3

    debts = group.simplify_debts()

    assert set(debts) == {
        Debt(Money(Decimal("10.001"), "EUR"), member_a, member_c),
        Debt(Money(Decimal("5.001"), "EUR"), member_b, member_c),
    }
    assert len(debts) == 2
    assert group.debts == original_debts
    assert group.transactions == original_transactions


def test_settles_group_with_minimum_number_of_payments() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    member_d = Member("D", "D")
    member_e = Member("E", "E")
    group = Group(
        "group", "Group", _members=[member_a, member_b, member_c, member_d, member_e]
    )
    group.add_expense(
        create_expense(payer=member_d, receiver=member_a, amount="8", expense_id="A")
    )
    group.add_expense(
        create_expense(payer=member_d, receiver=member_b, amount="4", expense_id="B")
    )
    group.add_expense(
        create_expense(payer=member_e, receiver=member_b, amount="3", expense_id="C")
    )
    group.add_expense(
        create_expense(payer=member_e, receiver=member_c, amount="5", expense_id="D")
    )

    debts = group.simplify_debts()

    assert len(debts) == 3
    assert set(debts) == {
        Debt(Money(Decimal("8"), "EUR"), member_a, member_e),
        Debt(Money(Decimal("7"), "EUR"), member_b, member_d),
        Debt(Money(Decimal("5"), "EUR"), member_c, member_d),
    }


def test_returns_same_debts_when_member_and_expense_order_changes() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    member_d = Member("D", "D")
    expense_a = create_expense(
        payer=member_c, receiver=member_a, amount="5", expense_id="A"
    )
    expense_b = create_expense(
        payer=member_d, receiver=member_b, amount="5", expense_id="B"
    )
    group = Group("group", "Group", _members=[member_a, member_b, member_c, member_d])
    group.add_expense(expense_a)
    group.add_expense(expense_b)
    reordered_group = Group(
        "group", "Group", _members=[member_d, member_c, member_b, member_a]
    )
    reordered_group.add_expense(expense_b)
    reordered_group.add_expense(expense_a)

    debts = group.simplify_debts()

    assert debts == reordered_group.simplify_debts()


def test_returns_no_debts_when_all_members_are_settled() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    member_d = Member("D", "D")
    group = Group("group", "Group", _members=[member_a, member_b, member_c, member_d])
    group.add_expense(
        create_expense(payer=member_b, receiver=member_a, amount="5", expense_id="A")
    )
    group.add_expense(
        create_expense(payer=member_c, receiver=member_b, amount="5", expense_id="B")
    )
    group.add_expense(
        create_expense(payer=member_a, receiver=member_c, amount="5", expense_id="C")
    )
    original_debts = group.debts
    assert len(original_debts) == 3

    assert group.simplify_debts() == []
    assert group.debts == original_debts
