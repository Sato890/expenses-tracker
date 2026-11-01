from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category
from app.services import (
    GroupNotFoundError,
    InvalidCategoryError,
    InvalidExpenseRequestError,
    InvalidParticipantError,
    create_equal_expense,
)


class FakeGroups:
    def __init__(self, group: Group | None) -> None:
        self.group = group

    def get(self, group_id: str) -> Group | None:
        return (
            self.group if self.group is not None and self.group.id == group_id else None
        )


class FakeCategories:
    def __init__(self, category: Category | None) -> None:
        self.category = category

    def get(self, category_id: object) -> Category | None:
        if self.category is not None and self.category.id == category_id:
            return self.category
        return None


class FakeSession:
    def __init__(self, commit_error: Exception | None = None) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.commit_error = commit_error

    def commit(self) -> None:
        self.commits += 1
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        self.rollbacks += 1


def test_create_equal_expense_saves_selected_members_and_commits_once() -> None:
    group = Group(
        "household",
        "Household",
        _members=[
            Member("alex", "Alex"),
            Member("bea", "Bea"),
            Member("cam", "Cam"),
        ],
    )
    category = Category("Groceries")
    session = FakeSession()

    expense = create_equal_expense(
        "household",
        Money(Decimal("10"), "EUR"),
        "alex",
        date(2026, 10, 31),
        category.id,
        ["bea", "alex", "cam"],
        FakeGroups(group),
        FakeCategories(category),
        session,
    )

    assert expense.expense_id
    assert group.transactions == (expense,)
    assert expense.payer is group.members[0]
    assert expense.category is category
    assert [(item.receiver.id, item.share.amount) for item in expense.allocations] == [
        ("alex", Decimal("3.333333333333333333")),
        ("bea", Decimal("3.333333333333333334")),
        ("cam", Decimal("3.333333333333333333")),
    ]
    assert (session.commits, session.rollbacks) == (1, 0)


@pytest.mark.parametrize(
    ("group_exists", "category_exists", "amount", "payer_id", "receiver_ids", "error"),
    [
        (False, True, "10", "alex", ["alex"], GroupNotFoundError),
        (True, False, "10", "alex", ["alex"], InvalidCategoryError),
        (True, True, "0", "alex", ["alex"], ValueError),
        (True, True, "10", "alex", [], ValueError),
        (True, True, "10", "alex", ["alex", "alex"], ValueError),
        (True, True, "10", "unknown", ["alex"], InvalidParticipantError),
        (True, True, "10", "alex", ["unknown"], InvalidParticipantError),
    ],
)
def test_create_equal_expense_rejects_invalid_context_without_committing(
    group_exists: bool,
    category_exists: bool,
    amount: str,
    payer_id: str,
    receiver_ids: list[str],
    error: type[Exception],
) -> None:
    group = Group("household", "Household", _members=[Member("alex", "Alex")])
    category = Category("Groceries")
    session = FakeSession()

    with pytest.raises(error):
        create_equal_expense(
            "household",
            Money(Decimal(amount), "EUR"),
            payer_id,
            date(2026, 10, 31),
            category.id if category_exists else uuid4(),
            receiver_ids,
            FakeGroups(group if group_exists else None),
            FakeCategories(category),
            session,
        )

    assert group.transactions == ()
    assert (session.commits, session.rollbacks) == (0, 1)


def test_rejects_equal_expense_below_one_allocation_unit_per_receiver() -> None:
    members = [Member(str(index), str(index)) for index in range(101)]
    group = Group("household", "Household", _members=members)
    category = Category("Groceries")
    session = FakeSession()

    with pytest.raises(
        InvalidExpenseRequestError,
        match="The expense amount must provide at least one allocation unit per receiver",
    ):
        create_equal_expense(
            group.id,
            Money(Decimal("0.0000000000000001"), "EUR"),
            members[0].id,
            date(2026, 10, 31),
            category.id,
            [member.id for member in members],
            FakeGroups(group),
            FakeCategories(category),
            session,
        )

    assert group.transactions == ()
    assert (session.commits, session.rollbacks) == (0, 1)


def test_accepts_equal_expense_at_one_allocation_unit_per_receiver() -> None:
    members = [Member(str(index), str(index)) for index in range(100)]
    group = Group("household", "Household", _members=members)
    category = Category("Groceries")
    session = FakeSession()
    amount = Money(Decimal("0.0000000000000001"), "EUR")

    expense = create_equal_expense(
        group.id,
        amount,
        members[0].id,
        date(2026, 10, 31),
        category.id,
        [member.id for member in members],
        FakeGroups(group),
        FakeCategories(category),
        session,
    )

    assert [allocation.share for allocation in expense.allocations] == [
        Money(Decimal("1e-18"), "EUR")
    ] * 100


def test_rolls_back_and_propagates_the_original_commit_error() -> None:
    group = Group("household", "Household", _members=[Member("alex", "Alex")])
    category = Category("Groceries")
    commit_error = RuntimeError("Commit failed")
    session = FakeSession(commit_error)

    with pytest.raises(RuntimeError) as e:
        create_equal_expense(
            group.id,
            Money(Decimal("10"), "EUR"),
            "alex",
            date(2026, 10, 31),
            category.id,
            ["alex"],
            FakeGroups(group),
            FakeCategories(category),
            session,
        )

    assert e.value is commit_error
    assert (session.commits, session.rollbacks) == (1, 1)
