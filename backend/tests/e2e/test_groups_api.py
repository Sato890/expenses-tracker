from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.adapters.orm import groups


def test_lists_groups_by_name_then_id(
    schema_engine: Engine, client: TestClient
) -> None:
    with Session(schema_engine) as session:
        session.execute(
            groups.insert(),
            [
                {"id": "group-2", "name": "Trip"},
                {"id": "group-3", "name": "Home"},
                {"id": "group-1", "name": "Home"},
            ],
        )
        session.commit()

    response = client.get("/groups")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "group-1", "name": "Home"},
        {"id": "group-3", "name": "Home"},
        {"id": "group-2", "name": "Trip"},
    ]


def test_lists_no_groups(client: TestClient) -> None:
    response = client.get("/groups")
    assert response.status_code == 200
    assert response.json() == []


def test_creates_group(schema_engine: Engine, client: TestClient) -> None:
    response = client.post("/groups", json={"name": "  Home  "})

    assert response.status_code == 201
    group = response.json()
    assert group["id"]
    assert group["name"] == "Home"

    with Session(schema_engine) as session:
        saved = session.execute(
            select(groups.c.id, groups.c.name).where(groups.c.id == group["id"])
        ).one()
        assert (saved.id, saved.name) == (group["id"], "Home")


def test_rejects_invalid_group_name(client: TestClient) -> None:
    response = client.post("/groups", json={"name": "  "})

    assert response.status_code == 422
