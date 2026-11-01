from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.adapters.repository import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyGroupRepository,
)
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense
from app.services import (
    GroupNotFoundError,
    create_equal_expense,
    get_group_settlement_amounts,
)


def test_equal_expense_survives_a_fresh_session(schema_engine: Engine) -> None:
    group = Group(
        "household",
        "Household",
        _members=[Member("alex", "Alex"), Member("bea", "Bea")],
    )
    category = Category("Groceries")
    category_id = category.id
    with Session(schema_engine) as session:
        SqlAlchemyGroupRepository(session).add(group)
        session.add(category)
        session.commit()

    with Session(schema_engine) as session:
        created = create_equal_expense(
            "household",
            Money(Decimal("10.005"), "EUR"),
            "alex",
            date(2026, 10, 31),
            category_id,
            ["bea", "alex"],
            SqlAlchemyGroupRepository(session),
            SqlAlchemyCategoryRepository(session),
            session,
        )
        expense_id = created.expense_id

    with Session(schema_engine) as session:
        loaded = SqlAlchemyGroupRepository(session).get("household")
        assert loaded is not None
        assert len(loaded.transactions) == 1
        expense = loaded.transactions[0]
        assert isinstance(expense, Expense)
        assert expense.expense_id == expense_id
        assert expense.amount.amount == Decimal("10.005")
        assert expense.payer is loaded.members[0]
        assert expense.category.id == category_id
        assert [
            (item.receiver.id, item.share.amount) for item in expense.allocations
        ] == [
            ("alex", Decimal("5.0025")),
            ("bea", Decimal("5.0025")),
        ]


def test_settlement_amounts_use_complete_persisted_group_history(
    schema_engine: Engine,
) -> None:
    category = Category("Groceries")
    category_id = category.id
    with Session(schema_engine) as session:
        session.add_all(
            [
                Group(
                    "household",
                    "Household",
                    _members=[
                        Member("alex", "Alex"),
                        Member("bea", "Bea"),
                        Member("cam", "Cam"),
                    ],
                ),
                Group("other", "Other", _members=[Member("dan", "Dan")]),
                Group("empty", "Empty"),
                category,
            ]
        )
        session.commit()

    with Session(schema_engine) as session:
        for amount in ("10.005", "2.001"):
            create_equal_expense(
                "household",
                Money(Decimal(amount), "EUR"),
                "alex",
                date(2026, 10, 31),
                category_id,
                ["alex", "bea"],
                SqlAlchemyGroupRepository(session),
                SqlAlchemyCategoryRepository(session),
                session,
            )

    with Session(schema_engine) as session:
        groups = SqlAlchemyGroupRepository(session)
        amounts = get_group_settlement_amounts("household", groups)
        assert {member.id: amount for member, amount in amounts.items()} == {
            "alex": Money(Decimal("6.003"), "EUR"),
            "bea": Money(Decimal("-6.003"), "EUR"),
            "cam": Money(Decimal("0"), "EUR"),
        }
        assert {
            member.id: amount
            for member, amount in get_group_settlement_amounts("other", groups).items()
        } == {"dan": Money(Decimal("0"), "EUR")}
        assert get_group_settlement_amounts("empty", groups) == {}
        with pytest.raises(GroupNotFoundError):
            get_group_settlement_amounts("missing", groups)
