from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.adapters.orm import groups


def test_lists_groups(schema_engine: Engine, client: TestClient) -> None:
    with Session(schema_engine) as session:
        session.execute(
            groups.insert(),
            [
                {"id": "group-1", "name": "Home"},
                {"id": "group-2", "name": "Trip"},
            ],
        )
        session.commit()

    response = client.get("/groups")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "group-1", "name": "Home"},
        {"id": "group-2", "name": "Trip"},
    ]


def test_lists_no_groups(client: TestClient) -> None:
    response = client.get("/groups")
    assert response.status_code == 200
    assert response.json() == []
