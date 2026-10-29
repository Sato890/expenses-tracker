from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.adapters.orm import mapper_registry, metadata, start_mappers
from app.adapters.repository import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyGroupRepository,
)
from app.config import ENV_FILE
from app.domain.allocation import Allocation
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense


class IntegrationDatabaseSettings(BaseSettings):
    test_database_url: PostgresDsn

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, dotenv_filtering="only_existing"
    )


@pytest.fixture
def schema_engine() -> Iterator[Engine]:
    database_url = str(IntegrationDatabaseSettings().test_database_url)

    schema = f"test_{uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(CreateSchema(schema))

    schema_engine = create_engine(
        database_url,
        connect_args={"options": f"-csearch_path={schema}"},
    )

    try:
        metadata.create_all(schema_engine)
        start_mappers()
        yield schema_engine
    finally:
        mapper_registry.dispose()
        schema_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()


def create_group(group_id: str = "group-1") -> Group:
    return Group(
        group_id,
        "Household",
        _members=[Member("member-1", "Satoshi"), Member("member-2", "Ilaria")],
    )


def create_expense(
    group: Group,
    category: Category,
    expense_id: str = "expense-1",
    amount: str = "10",
) -> Expense:
    payer, receiver = group.members
    money = Money(Decimal(amount), "EUR")
    return Expense(
        expense_id,
        money,
        payer,
        date(2026, 10, 1),
        category,
        Allocation(receiver, money),
    )


def test_repository_can_reconstruct_group_with_expenses(
    schema_engine: Engine,
) -> None:
    group = create_group()
    payer, receiver = group.members
    category = Category("Other")
    category_id = category.id
    group.add_expense(
        Expense(
            "expense-1",
            Money(Decimal("10"), "EUR"),
            payer,
            date(2026, 10, 1),
            category,
            [
                Allocation(receiver, Money(Decimal("6.666666666666666667"), "EUR")),
                Allocation(payer, Money(Decimal("3.333333333333333333"), "EUR")),
            ],
        )
    )
    with Session(schema_engine) as session:
        SqlAlchemyGroupRepository(session).add(group)
        session.commit()

    with Session(schema_engine) as session:
        loaded = SqlAlchemyGroupRepository(session).get("group-1")
        expected_group = create_group()
        expected_expense = Expense(
            "expense-1",
            Money(Decimal("10"), "EUR"),
            Member("member-1", "Satoshi"),
            date(2026, 10, 1),
            Category("Other", id=category_id),
            [
                Allocation(
                    Member("member-1", "Satoshi"),
                    Money(Decimal("3.333333333333333333"), "EUR"),
                ),
                Allocation(
                    Member("member-2", "Ilaria"),
                    Money(Decimal("6.666666666666666667"), "EUR"),
                ),
            ],
        )
        expected_group.add_expense(expected_expense)

        assert loaded == expected_group


def test_keeps_expenses_within_their_group(
    schema_engine: Engine,
) -> None:
    category = Category("Other")
    category_id = category.id
    with Session(schema_engine) as session:
        repository = SqlAlchemyGroupRepository(session)
        for group_id, amount in (("group-1", "10"), ("group-2", "20")):
            group = create_group(group_id)
            group.add_expense(create_expense(group, category, amount=amount))
            repository.add(group)
        session.commit()

    with Session(schema_engine) as session:
        repository = SqlAlchemyGroupRepository(session)
        first = repository.get("group-1")
        second = repository.get("group-2")
        assert first is not None
        assert second is not None
        for group, amount in ((first, "10"), (second, "20")):
            expected_group = create_group(group.id)
            expected_group.add_expense(
                create_expense(
                    expected_group, Category("Other", id=category_id), amount=amount
                )
            )
            assert group == expected_group
            expense = group.transactions[0]
            assert expense.payer is group.members[0]
            assert expense.allocations[0].receiver is group.members[1]
        assert first.members[0] is not second.members[0]
        assert first.members[1] is not second.members[1]


def test_preserves_history_when_two_sessions_append(
    schema_engine: Engine,
) -> None:
    group = create_group()
    group.add_expense(create_expense(group, Category("Other"), "original"))
    with Session(schema_engine) as session:
        SqlAlchemyGroupRepository(session).add(group)
        session.commit()

    with (
        Session(schema_engine) as first_session,
        Session(schema_engine) as second_session,
    ):
        first = SqlAlchemyGroupRepository(first_session).get("group-1")
        second = SqlAlchemyGroupRepository(second_session).get("group-1")
        assert first is not None
        assert second is not None

        for session, loaded, expense_id in (
            (first_session, first, "append-1"),
            (second_session, second, "append-2"),
        ):
            loaded.add_expense(
                create_expense(loaded, loaded.transactions[0].category, expense_id)
            )
            session.commit()

    with Session(schema_engine) as session:
        loaded = SqlAlchemyGroupRepository(session).get("group-1")
        assert loaded is not None
        assert {expense.expense_id for expense in loaded.transactions} == {
            "original",
            "append-1",
            "append-2",
        }


def test_repository_can_retrieve_category_by_id(schema_engine: Engine) -> None:
    category = Category("Groceries")
    category_id = category.id
    with Session(schema_engine) as session:
        session.add_all([category, Category("Transport")])
        session.commit()

    with Session(schema_engine) as session:
        loaded = SqlAlchemyCategoryRepository(session).get(category_id)

        assert loaded is not None
        assert (loaded.id, loaded.name) == (category_id, "Groceries")


def test_repository_returns_none_for_missing_category(schema_engine: Engine) -> None:
    with Session(schema_engine) as session:
        assert SqlAlchemyCategoryRepository(session).get(uuid4()) is None
