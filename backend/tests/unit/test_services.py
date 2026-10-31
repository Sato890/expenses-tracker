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
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

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
