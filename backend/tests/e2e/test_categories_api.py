from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.adapters.orm import categories


def test_lists_categories(schema_engine: Engine, client: TestClient) -> None:
    groceries_id = UUID("0bacd5bc-13a0-430e-a8b3-1dbf69194e8b")
    transport_id = UUID("58a37aee-0429-4cbd-adef-ad86c144ae7b")
    with Session(schema_engine) as session:
        session.execute(
            categories.insert(),
            [
                {"id": transport_id, "name": "Transport"},
                {"id": groceries_id, "name": "Groceries"},
            ],
        )
        session.commit()

    response = client.get("/categories")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": str(groceries_id), "name": "Groceries"},
            {"id": str(transport_id), "name": "Transport"},
        ]
    }


def test_lists_no_categories(client: TestClient) -> None:
    response = client.get("/categories")

    assert response.status_code == 200
    assert response.json() == {"items": []}
