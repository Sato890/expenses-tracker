from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.adapters.orm import categories, groups, members

CATEGORY_ID = UUID("0bacd5bc-13a0-430e-a8b3-1dbf69194e8b")


def test_reads_persisted_settlement_amounts_after_expense_and_history(
    schema_engine: Engine, client: TestClient
) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="household", name="Household"))
        session.execute(
            members.insert(),
            [
                {"group_id": "household", "id": "alex", "name": "Alex"},
                {"group_id": "household", "id": "bea", "name": "Bea"},
                {"group_id": "household", "id": "cam", "name": "Cam"},
            ],
        )
        session.execute(categories.insert().values(id=CATEGORY_ID, name="Groceries"))
        session.commit()

    created = client.post(
        "/groups/household/transactions",
        json={
            "type": "expense",
            "amount": "10.005",
            "payer_id": "alex",
            "date": "2026-11-01",
            "category_id": str(CATEGORY_ID),
            "split": {"type": "equal", "receiver_ids": ["alex", "bea"]},
        },
    )
    assert created.status_code == 201

    history = client.get("/groups/household/transactions")
    assert history.status_code == 200
    assert history.json()["items"] == [created.json()]

    amounts = client.get("/groups/household/settlement-amounts")
    assert amounts.status_code == 200
    assert amounts.json() == {
        "group_id": "household",
        "currency": "EUR",
        "items": [
            {"member_id": "alex", "amount": "5.002500000000000000"},
            {"member_id": "bea", "amount": "-5.002500000000000000"},
            {"member_id": "cam", "amount": "0"},
        ],
    }


def test_reads_empty_group_and_rejects_missing_group(
    schema_engine: Engine, client: TestClient
) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="empty", name="Empty"))
        session.commit()

    response = client.get("/groups/empty/settlement-amounts")
    assert response.status_code == 200
    assert response.json() == {"group_id": "empty", "currency": "EUR", "items": []}

    missing = client.get("/groups/missing/settlement-amounts")
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {"code": "GROUP_NOT_FOUND", "message": "Group not found."}
    }
