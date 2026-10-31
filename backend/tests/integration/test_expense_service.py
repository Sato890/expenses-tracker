from datetime import date
from decimal import Decimal

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
from app.services import create_equal_expense


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
