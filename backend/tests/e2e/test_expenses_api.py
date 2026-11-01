from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.adapters.orm import allocations, categories, expenses, groups, members

GROUP_ID = "household"
CATEGORY_ID = UUID("0bacd5bc-13a0-430e-a8b3-1dbf69194e8b")


@pytest.fixture
def prepared_expense_group(schema_engine: Engine) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id=GROUP_ID, name="Household"))
        session.execute(
            members.insert(),
            [
                {"group_id": GROUP_ID, "id": "alex", "name": "Alex"},
                {"group_id": GROUP_ID, "id": "bea", "name": "Bea"},
            ],
        )
        session.execute(categories.insert().values(id=CATEGORY_ID, name="Groceries"))
        session.commit()


def expense_request() -> dict[str, object]:
    return {
        "type": "expense",
        "amount": "10.005",
        "payer_id": "alex",
        "date": "2026-11-01",
        "category_id": str(CATEGORY_ID),
        "split": {"type": "equal", "receiver_ids": ["bea", "alex"]},
    }


def test_creates_equal_expense_with_full_precision_and_persists_allocations(
    schema_engine: Engine, client: TestClient, prepared_expense_group: None
) -> None:
    response = client.post(f"/groups/{GROUP_ID}/transactions", json=expense_request())

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "group_id": GROUP_ID,
        "type": "expense",
        "amount": "10.005",
        "currency": "EUR",
        "payer_id": "alex",
        "date": "2026-11-01",
        "category_id": str(CATEGORY_ID),
        "allocations": [
            {"receiver_id": "alex", "amount": "5.002500000000000000"},
            {"receiver_id": "bea", "amount": "5.002500000000000000"},
        ],
    }
    assert body["id"]
    assert "location" not in response.headers

    with Session(schema_engine) as session:
        saved = session.execute(
            select(expenses.c.amount, expenses.c.date).where(
                expenses.c.group_id == GROUP_ID, expenses.c.id == body["id"]
            )
        ).one()
        saved_shares = session.execute(
            select(allocations.c.receiver_id, allocations.c.amount)
            .where(
                allocations.c.group_id == GROUP_ID,
                allocations.c.expense_id == body["id"],
            )
            .order_by(allocations.c.receiver_id)
        ).all()
    assert saved == (Decimal("10.005"), date(2026, 11, 1))
    assert saved_shares == [("alex", Decimal("5.0025")), ("bea", Decimal("5.0025"))]
