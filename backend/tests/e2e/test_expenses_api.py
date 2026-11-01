from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.adapters.orm import allocations, categories, expenses, groups, members
from app.main import app
from app.routers import expenses as expense_routes

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


@pytest.mark.usefixtures("prepared_expense_group")
def test_creates_equal_expense_with_full_precision_and_persists_allocations(
    schema_engine: Engine, client: TestClient
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


@pytest.mark.usefixtures("prepared_expense_group")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", "0"),
        ("amount", "1e2"),
        ("amount", "١٠"),
        ("amount", "1234567890123456789"),
        ("amount", 10),
        ("date", "2026-02-30"),
        ("date", 1735689600),
        ("type", "settlement"),
        ("currency", "USD"),
        ("split", {"type": "exact", "receiver_ids": ["alex"]}),
        ("split", {"type": "equal", "receiver_ids": ["alex"], "note": "x"}),
    ],
)
def test_rejects_invalid_expense_input_without_writing(
    schema_engine: Engine,
    client: TestClient,
    field: str,
    value: object,
) -> None:
    payload = expense_request()
    payload[field] = value

    response = client.post(f"/groups/{GROUP_ID}/transactions", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "INVALID_REQUEST", "message": "Invalid request."}
    }
    with Session(schema_engine) as session:
        assert session.execute(select(expenses.c.id)).all() == []


@pytest.mark.usefixtures("prepared_expense_group")
@pytest.mark.parametrize(
    ("change", "status_code", "error_code", "message"),
    [
        ("missing_group", 404, "GROUP_NOT_FOUND", "Group not found."),
        ("missing_category", 422, "INVALID_CATEGORY", "Invalid category."),
        (
            "unknown_payer",
            422,
            "INVALID_PARTICIPANT",
            "A selected participant does not belong to this group.",
        ),
        (
            "unknown_receiver",
            422,
            "INVALID_PARTICIPANT",
            "A selected participant does not belong to this group.",
        ),
        ("duplicate_receiver", 422, "INVALID_REQUEST", "Invalid request."),
        ("empty_receiver", 422, "INVALID_REQUEST", "Invalid request."),
    ],
)
def test_rejects_invalid_expense_context_without_writing(
    schema_engine: Engine,
    client: TestClient,
    change: str,
    status_code: int,
    error_code: str,
    message: str,
) -> None:
    payload = expense_request()
    group_id = GROUP_ID
    if change == "missing_group":
        group_id = "missing"
    elif change == "missing_category":
        payload["category_id"] = "58a37aee-0429-4cbd-adef-ad86c144ae7b"
    elif change == "unknown_payer":
        payload["payer_id"] = "other-group-member"
    elif change == "unknown_receiver":
        payload["split"] = {"type": "equal", "receiver_ids": ["unknown"]}
    elif change == "duplicate_receiver":
        payload["split"] = {"type": "equal", "receiver_ids": ["alex", "alex"]}
    else:
        payload["split"] = {"type": "equal", "receiver_ids": []}

    response = client.post(f"/groups/{group_id}/transactions", json=payload)

    assert response.status_code == status_code
    assert response.json() == {"error": {"code": error_code, "message": message}}
    with Session(schema_engine) as session:
        assert session.execute(select(expenses.c.id)).all() == []


def test_rejects_malformed_expense_json(client: TestClient) -> None:
    response = client.post(
        f"/groups/{GROUP_ID}/transactions",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "INVALID_REQUEST", "message": "Invalid request."}
    }


def test_hides_unexpected_expense_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("secret database detail")

    monkeypatch.setattr(expense_routes, "create_equal_expense", fail)
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post(
            f"/groups/{GROUP_ID}/transactions", json=expense_request()
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Internal server error."}
    }
