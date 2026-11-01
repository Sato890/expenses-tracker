from datetime import date
from decimal import Context, Decimal, localcontext

import pytest

from app.domain.allocation import Allocation, allocate_equally
from app.domain.debt import Debt
from app.domain.group import Group
from app.domain.identity import Member, User
from app.domain.money import Money
from app.domain.transaction import Category, Expense, Settlement


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


def create_settlement(
    payer: Member,
    receiver: Member,
    amount: str,
    settlement_id: str = "settlement",
) -> Settlement:
    return Settlement(
        settlement_id, Money(Decimal(amount), "EUR"), payer, date.today(), receiver
    )


def test_derives_debts_from_current_transactions() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    group.add_expense(create_expense(member_a, member_b, "5", "expense-a"))

    assert group.debts == [Debt(Money(Decimal("5"), "EUR"), member_b, member_a)]

    group.add_expense(create_expense(member_b, member_a, "4", "expense-b"))

    assert group.debts == [Debt(Money(Decimal("1"), "EUR"), member_b, member_a)]


def test_calculates_settlement_amounts_for_every_member() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    member_c = Member("C", "C")
    member_d = Member("D", "D")

    group = Group("group", "Group", _members=[member_a, member_b, member_c, member_d])
    group.add_expense(create_expense(member_a, member_b, "3.0005", "expense-a"))
    group.add_expense(create_expense(member_c, member_a, "2.0005", "expense-b"))

    settlement_amounts = group.calculate_member_settlement_amounts()

    assert settlement_amounts == {
        member_a: Money(Decimal("1.0000"), "EUR"),
        member_b: Money(Decimal("-3.0005"), "EUR"),
        member_c: Money(Decimal("2.0005"), "EUR"),
        member_d: Money(Decimal("0"), "EUR"),
    }
    assert sum(amount.amount for amount in settlement_amounts.values()) == Decimal("0")


def test_adds_valid_expense() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    expense = create_expense(payer, receiver, "5")

    group.add_expense(expense)

    assert group.transactions == (expense,)


def test_rejects_expense_from_non_member_payer() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[receiver])

    with pytest.raises(ValueError, match="Payer is not in the group"):
        group.add_expense(create_expense(payer, receiver, "5"))

    assert group.transactions == ()


def test_rejects_expense_for_non_member_receiver() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer])

    with pytest.raises(ValueError, match="Receiver is not in the group"):
        group.add_expense(create_expense(payer, receiver, "5"))

    assert group.transactions == ()


def test_rejects_duplicate_allocation_receivers_without_adding_expense() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    expense = Expense(
        "expense",
        Money(Decimal("5"), "EUR"),
        payer,
        date.today(),
        Category("Other"),
        [
            Allocation(receiver, Money(Decimal("2"), "EUR")),
            Allocation(receiver, Money(Decimal("3"), "EUR")),
        ],
    )

    with pytest.raises(ValueError, match="Allocation receivers must be unique"):
        group.add_expense(expense)

    assert group.transactions == ()


@pytest.mark.parametrize("other_group_role", ["payer", "receiver"])
def test_rejects_expense_member_from_another_group_with_the_same_id(
    other_group_role: str,
) -> None:
    payer = Member("A", "Alex")
    receiver = Member("B", "Bea")
    group = Group("group-a", "Group A", _members=[payer, receiver])
    other_group = Group(
        "group-b",
        "Group B",
        _members=[Member("A", "Other Alex"), Member("B", "Other Bea")],
    )
    other_payer, other_receiver = other_group.members

    with pytest.raises(
        ValueError, match=f"{other_group_role.capitalize()} is not in the group"
    ):
        group.add_expense(
            create_expense(
                other_payer if other_group_role == "payer" else payer,
                other_receiver if other_group_role == "receiver" else receiver,
                "5",
            )
        )

    assert group.transactions == ()


def test_rejects_expense_with_invalid_allocations() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
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
    group = Group("group", "Group", _members=[payer, receiver])
    expense = create_expense(payer, receiver, "5", "expense")
    duplicate = create_expense(payer, receiver, "4", "expense")
    group.add_expense(expense)

    with pytest.raises(ValueError, match="Expense ID already exists"):
        group.add_expense(duplicate)

    assert group.transactions == (expense,)


def test_removes_expense_by_id() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    expense_a = create_expense(payer, receiver, "5", "expense-a")
    expense_b = create_expense(payer, receiver, "5", "expense-b")
    group.add_expense(expense_a)
    group.add_expense(expense_b)

    group.remove_expense("expense-a")

    assert group.transactions == (expense_b,)


def test_edits_expense_by_id() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    original = create_expense(member_a, member_b, "5", "expense")
    replacement = create_expense(member_b, member_a, "4", "expense")
    group.add_expense(original)

    group.edit_expense(replacement)

    assert group.transactions == (replacement,)
    assert group.debts == [Debt(Money(Decimal("4"), "EUR"), member_a, member_b)]


def test_rejects_invalid_expense_edit_without_changing_transactions() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
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


def test_rejects_duplicate_member_ids_at_construction() -> None:
    member = Member("A", "Alice")
    duplicate = Member("A", "Bob")

    with pytest.raises(ValueError, match="Member ID already exists in the group"):
        Group("group", "Group", _members=[member, duplicate])


def test_rejects_adding_duplicate_member_id() -> None:
    member = Member("A", "Alice")
    duplicate = Member("A", "Bob")
    group = Group("group", "Group", _members=[member])

    with pytest.raises(ValueError, match="Member ID already exists in the group"):
        group.add_member(duplicate)

    assert group.members == (member,)


def test_copies_members_supplied_at_construction() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    original_members = [payer, receiver]
    group = Group("group", "Group", _members=original_members)
    group.add_expense(create_expense(payer, receiver, "5"))

    original_members.remove(receiver)

    assert group.members == (payer, receiver)
    assert group.calculate_member_settlement_amounts() == {
        payer: Money(Decimal("5"), "EUR"),
        receiver: Money(Decimal("-5"), "EUR"),
    }


def test_removes_member_without_transactions() -> None:
    member = Member("A", "A")
    user = User("user", "User")
    group = Group("group", "Group", _members=[member], member_to_user={member: user})

    group.remove_member(member.id)

    assert group.members == ()
    assert group.member_to_user == {}


def test_rejects_removing_member_with_expense() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    group.add_expense(create_expense(payer, receiver, "5"))

    with pytest.raises(ValueError, match="associated transactions"):
        group.remove_member(receiver.id)

    assert group.members == (payer, receiver)


def test_reduces_debt_after_partial_settlement() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    group.add_expense(create_expense(member_a, member_b, "10"))

    group.add_settlement(create_settlement(member_b, member_a, "4"))

    assert group.calculate_member_settlement_amounts() == {
        member_a: Money(Decimal("6"), "EUR"),
        member_b: Money(Decimal("-6"), "EUR"),
    }


def test_clears_debt_after_full_settlement() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    group.add_expense(create_expense(member_a, member_b, "10"))

    group.add_settlement(create_settlement(member_b, member_a, "10"))

    assert group.debts == []
    assert group.calculate_member_settlement_amounts() == {
        member_a: Money(Decimal("0"), "EUR"),
        member_b: Money(Decimal("0"), "EUR"),
    }


def test_reverses_debt_after_excess_settlement() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    group.add_expense(create_expense(member_a, member_b, "10"))

    group.add_settlement(create_settlement(member_b, member_a, "12"))

    assert group.calculate_member_settlement_amounts() == {
        member_a: Money(Decimal("-2"), "EUR"),
        member_b: Money(Decimal("2"), "EUR"),
    }


def test_adds_valid_settlement() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    settlement = create_settlement(payer, receiver, "5")

    group.add_settlement(settlement)

    assert group.transactions == (settlement,)
    assert group.debts == [Debt(Money(Decimal("5"), "EUR"), receiver, payer)]


@pytest.mark.parametrize("missing_role", ["payer", "receiver"])
def test_rejects_settlement_with_non_member(missing_role: str) -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    members = [receiver] if missing_role == "payer" else [payer]
    group = Group("group", "Group", _members=members)

    with pytest.raises(
        ValueError, match=f"{missing_role.capitalize()} is not in the group"
    ):
        group.add_settlement(create_settlement(payer, receiver, "5"))

    assert group.transactions == ()


@pytest.mark.parametrize("other_group_role", ["payer", "receiver"])
def test_rejects_settlement_member_from_another_group_with_the_same_id(
    other_group_role: str,
) -> None:
    payer = Member("A", "Alex")
    receiver = Member("B", "Bea")
    group = Group("group-a", "Group A", _members=[payer, receiver])
    other_group = Group(
        "group-b",
        "Group B",
        _members=[Member("A", "Other Alex"), Member("B", "Other Bea")],
    )
    other_payer, other_receiver = other_group.members

    with pytest.raises(
        ValueError, match=f"{other_group_role.capitalize()} is not in the group"
    ):
        group.add_settlement(
            create_settlement(
                other_payer if other_group_role == "payer" else payer,
                other_receiver if other_group_role == "receiver" else receiver,
                "5",
            )
        )

    assert group.transactions == ()


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_rejects_nonpositive_settlement(amount: str) -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])

    with pytest.raises(ValueError, match="amount must be positive"):
        group.add_settlement(create_settlement(payer, receiver, amount))

    assert group.transactions == ()


def test_rejects_duplicate_settlement_id() -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    original = create_settlement(payer, receiver, "5")
    group.add_settlement(original)

    with pytest.raises(ValueError, match="Settlement ID already exists"):
        group.add_settlement(create_settlement(payer, receiver, "4"))

    assert group.transactions == (original,)


def test_removes_settlement_by_id() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    expense = create_expense(member_a, member_b, "10", "shared-id")
    payment = create_settlement(member_b, member_a, "4", "shared-id")
    other_payment = create_settlement(member_b, member_a, "1", "other")
    group.add_expense(expense)
    group.add_settlement(payment)
    group.add_settlement(other_payment)

    group.remove_settlement("shared-id")

    assert group.transactions == (expense, other_payment)
    assert group.debts == [Debt(Money(Decimal("9"), "EUR"), member_b, member_a)]
    assert group.calculate_member_settlement_amounts() == {
        member_a: Money(Decimal("9"), "EUR"),
        member_b: Money(Decimal("-9"), "EUR"),
    }


def test_edits_settlement_by_id() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    expense = create_expense(member_a, member_b, "10", "shared-id")
    original = create_settlement(member_b, member_a, "4", "shared-id")
    replacement = create_settlement(member_b, member_a, "7", "shared-id")
    group.add_expense(expense)
    group.add_settlement(original)

    group.edit_settlement(replacement)

    assert group.transactions == (expense, replacement)
    assert group.debts == [Debt(Money(Decimal("3"), "EUR"), member_b, member_a)]
    assert group.calculate_member_settlement_amounts() == {
        member_a: Money(Decimal("3"), "EUR"),
        member_b: Money(Decimal("-3"), "EUR"),
    }


@pytest.mark.parametrize("invalid_field", ["amount", "payer", "receiver"])
def test_rejects_invalid_settlement_edit_without_changing_transactions(
    invalid_field: str,
) -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    outsider = Member("C", "C")
    group = Group("group", "Group", _members=[payer, receiver])
    original = create_settlement(payer, receiver, "5")
    group.add_settlement(original)
    replacement = create_settlement(
        outsider if invalid_field == "payer" else payer,
        outsider if invalid_field == "receiver" else receiver,
        "0" if invalid_field == "amount" else "4",
    )

    with pytest.raises(ValueError, match="positive|not in the group"):
        group.edit_settlement(replacement)

    assert group.transactions == (original,)


@pytest.mark.parametrize("operation", ["edit", "remove"])
def test_rejects_changing_missing_settlement(operation: str) -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    expense = create_expense(payer, receiver, "5", "missing")
    group.add_expense(expense)

    if operation == "edit":
        replacement = create_settlement(payer, receiver, "4", "missing")
        with pytest.raises(ValueError, match="Settlement is not in the group"):
            group.edit_settlement(replacement)
    else:
        with pytest.raises(ValueError, match="Settlement is not in the group"):
            group.remove_settlement("missing")

    assert group.transactions == (expense,)


@pytest.mark.parametrize("member_id", ["A", "B"])
def test_rejects_removing_member_with_settlement(member_id: str) -> None:
    payer = Member("A", "A")
    receiver = Member("B", "B")
    group = Group("group", "Group", _members=[payer, receiver])
    group.add_settlement(create_settlement(payer, receiver, "5"))

    with pytest.raises(ValueError, match="associated transactions"):
        group.remove_member(member_id)

    assert group.members == (payer, receiver)


def test_settlement_changes_debts_without_changing_spending() -> None:
    member_a = Member("A", "A")
    member_b = Member("B", "B")
    group = Group("group", "Group", _members=[member_a, member_b])
    expense = create_expense(member_a, member_b, "10.005")
    group.add_expense(expense)
    spending_before = sum(allocation.share.amount for allocation in expense.allocations)

    group.add_settlement(create_settlement(member_b, member_a, "4.0025"))

    spending_after = sum(
        allocation.share.amount
        for transaction in group.transactions
        if isinstance(transaction, Expense)
        for allocation in transaction.allocations
    )
    assert spending_after == spending_before == Decimal("10.005")
    assert group.debts == [Debt(Money(Decimal("6.0025"), "EUR"), member_b, member_a)]
    amounts = group.calculate_member_settlement_amounts()
    assert amounts == {
        member_a: Money(Decimal("6.0025"), "EUR"),
        member_b: Money(Decimal("-6.0025"), "EUR"),
    }
    assert sum(amount.amount for amount in amounts.values()) == 0


@pytest.mark.parametrize("reverse_transactions", [False, True])
def test_preserves_exact_accumulated_settlement_amounts_in_any_transaction_order(
    reverse_transactions: bool,
) -> None:
    member_a, member_b, member_c = [Member(name, name) for name in ("a", "b", "c")]
    group = Group("group", "Group", _members=[member_a, member_b, member_c])
    expenses = [
        create_expense(member_a, member_b, "999999999999999999", str(index))
        for index in range(11)
    ]
    amount = Money(Decimal("1"), "EUR")
    expenses.append(
        Expense(
            "small",
            amount,
            member_a,
            date(2026, 10, 31),
            Category("Other"),
            allocate_equally(amount, [member_a, member_b, member_c]),
        )
    )
    for expense in reversed(expenses) if reverse_transactions else expenses:
        group.add_expense(expense)

    amounts = group.calculate_member_settlement_amounts()

    assert amounts == {
        member_a: Money(Decimal("10999999999999999989.666666666666666666"), "EUR"),
        member_b: Money(Decimal("-10999999999999999989.333333333333333333"), "EUR"),
        member_c: Money(Decimal("-0.333333333333333333"), "EUR"),
    }
    with localcontext(Context(prec=60)):
        assert sum(value.amount for value in amounts.values()) == Decimal("0")
