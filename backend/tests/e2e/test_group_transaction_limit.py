from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from queue import Queue
from threading import Event
from time import monotonic, sleep
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, func, select, text
from sqlalchemy.orm import Session

from app import services
from app.adapters.orm import allocations, expenses
from app.adapters.repository import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyGroupRepository,
)
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense
from app.services import GroupTransactionLimitReachedError, create_equal_expense


@pytest.fixture
def almost_full_group(schema_engine: Engine, request: pytest.FixtureRequest) -> UUID:
    category = Category("Groceries")
    category_id = category.id
    with Session(schema_engine) as session:
        session.add_all(
            [
                Group("household", "Household", _members=[Member("alex", "Alex")]),
                Group("other", "Other", _members=[Member("alex", "Alex")]),
                category,
            ]
        )
        session.commit()
        session.execute(
            text("""
            INSERT INTO expenses (group_id, id, amount, currency, payer_id, date, category_id)
            SELECT 'household', 'seed-' || n, 1, 'EUR', 'alex', DATE '2026-11-01', :category_id
            FROM generate_series(1, :expense_count) AS n
        """),
            {
                "category_id": category_id,
                "expense_count": getattr(request, "param", 49_999),
            },
        )
        session.execute(
            text("""
            INSERT INTO allocations (group_id, expense_id, receiver_id, amount, currency)
            SELECT group_id, id, 'alex', 1, 'EUR' FROM expenses
        """)
        )
        session.commit()
    return category_id


def record_expense(
    session: Session, category_id: UUID, group_id: str = "household"
) -> str:
    return create_equal_expense(
        group_id,
        Money(Decimal("1"), "EUR"),
        "alex",
        date(2026, 11, 1),
        category_id,
        ["alex"],
        SqlAlchemyGroupRepository(session),
        SqlAlchemyCategoryRepository(session),
        session,
    ).expense_id


def test_full_group_returns_conflict_and_deletion_frees_a_slot(
    schema_engine: Engine,
    client: TestClient,
    almost_full_group: UUID,
) -> None:
    payload = {
        "type": "expense",
        "amount": "1",
        "payer_id": "alex",
        "date": "2026-11-01",
        "category_id": str(almost_full_group),
        "split": {"type": "equal", "receiver_ids": ["alex"]},
    }
    url = "/groups/household/transactions"
    accepted = client.post(url, json=payload)
    assert accepted.status_code == 201
    rejected = client.post(url, json=payload)
    assert rejected.status_code == 409
    assert rejected.json() == {
        "error": {
            "code": "GROUP_TRANSACTION_LIMIT_REACHED",
            "message": "This group has reached the limit of 50,000 transactions.",
        }
    }
    with Session(schema_engine) as session:
        assert session.scalar(select(func.count()).select_from(expenses)) == 50_000
        assert session.scalar(select(func.count()).select_from(allocations)) == 50_000
        session.execute(
            expenses.update()
            .where(
                expenses.c.group_id == "household",
                expenses.c.id == accepted.json()["id"],
            )
            .values(date=date(2026, 11, 2))
        )
        session.commit()
        assert (
            SqlAlchemyGroupRepository(session).count_transactions_for_update(
                "household"
            )
            == 50_000
        )
        session.rollback()
        record_expense(session, almost_full_group, "other")
        expense = session.get(Expense, ("household", accepted.json()["id"]))
        session.delete(expense)
        session.commit()
    assert client.post(url, json=payload).status_code == 201
    with Session(schema_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(expenses)
                .where(expenses.c.group_id == "household")
            )
            == 50_000
        )


@pytest.mark.parametrize("rollback_first", [False, True])
@pytest.mark.parametrize("almost_full_group", [1], indirect=True)
def test_competing_creations_wait_and_recheck_capacity_after_commit_or_rollback(
    schema_engine: Engine,
    almost_full_group: UUID,
    rollback_first: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(services, "GROUP_TRANSACTION_LIMIT", 2)
    first_ready = Event()
    release_first = Event()
    second_pid: Queue[int] = Queue()

    def pause_before_commit(_session: Session) -> None:
        first_ready.set()
        assert release_first.wait(15)
        if rollback_first:
            raise RuntimeError("First creation failed")

    def first_request() -> str:
        with Session(schema_engine) as session:
            event.listen(session, "before_commit", pause_before_commit)
            return record_expense(session, almost_full_group)

    def second_request() -> str:
        with Session(schema_engine) as session:
            session.execute(text("SET LOCAL lock_timeout = '10s'"))
            second_pid.put(session.scalar(select(func.pg_backend_pid())))
            return record_expense(session, almost_full_group)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_request)
        try:
            assert first_ready.wait(15)
            second = pool.submit(second_request)
            pid = second_pid.get(timeout=5)
            deadline = monotonic() + 5
            with schema_engine.connect() as connection:
                while monotonic() < deadline:
                    if connection.scalar(
                        select(func.cardinality(func.pg_blocking_pids(pid)))
                    ):
                        break
                    sleep(0.01)
                else:
                    pytest.fail("Second creation did not wait for the group lock")
            with Session(schema_engine) as session:
                record_expense(session, almost_full_group, "other")
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(expenses)
                        .where(expenses.c.group_id == "household")
                    )
                    == 1
                )
        finally:
            release_first.set()
        if rollback_first:
            with pytest.raises(RuntimeError, match="First creation failed"):
                first.result(timeout=15)
            assert second.result(timeout=15)
        else:
            assert first.result(timeout=15)
            with pytest.raises(GroupTransactionLimitReachedError):
                second.result(timeout=15)

    with Session(schema_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(expenses)
                .where(expenses.c.group_id == "household")
            )
            == 2
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(allocations)
                .where(allocations.c.group_id == "household")
            )
            == 2
        )
