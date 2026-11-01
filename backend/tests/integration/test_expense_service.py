from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Connection, Engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable
from sqlalchemy.sql.dml import Insert

from app.adapters.orm import allocations, expenses
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


def test_rolls_back_partial_expense_writes_and_keeps_the_session_usable(
    schema_engine: Engine,
) -> None:
    category = Category("Groceries")
    category_id = category.id

    def record_expense(session: Session, amount: str) -> Expense:
        return create_equal_expense(
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

    expense_rows = select(expenses)
    allocation_rows = select(allocations).order_by(allocations.c.receiver_id)
    with Session(schema_engine) as session:
        session.add_all(
            [
                Group(
                    "household",
                    "Household",
                    _members=[
                        Member("alex", "Alex"),
                        Member("bea", "Bea"),
                    ],
                ),
                category,
            ]
        )
        session.commit()
        original_id = record_expense(session, "10.005").expense_id
        original_expenses = session.execute(expense_rows).all()
        original_allocations = session.execute(allocation_rows).all()

    allocation_error = RuntimeError("Allocation insert failed")

    def fail_allocation_insert(
        connection: Connection,
        statement: Executable,
        _multiparams: object,
        _params: object,
        _execution_options: object,
    ) -> None:
        if isinstance(statement, Insert) and statement.table is allocations:
            assert len(connection.execute(expense_rows).all()) == 2
            raise allocation_error

    with Session(schema_engine) as session:
        event.listen(schema_engine, "before_execute", fail_allocation_insert)
        try:
            with pytest.raises(RuntimeError) as e:
                record_expense(session, "4.002")
        finally:
            event.remove(schema_engine, "before_execute", fail_allocation_insert)
        assert e.value is allocation_error

        with Session(schema_engine) as fresh_session:
            assert fresh_session.execute(expense_rows).all() == original_expenses
            assert fresh_session.execute(allocation_rows).all() == original_allocations

        recovered_id = record_expense(session, "4.002").expense_id

    with Session(schema_engine) as session:
        assert set(session.scalars(select(expenses.c.id))) == {
            original_id,
            recovered_id,
        }
        assert set(session.scalars(select(allocations.c.expense_id))) == {
            original_id,
            recovered_id,
        }
