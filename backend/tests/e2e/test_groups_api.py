from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.adapters.orm import groups, members


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


def test_lists_group_members(schema_engine: Engine, client: TestClient) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="group-1", name="Home"))
        session.execute(groups.insert().values(id="group-2", name="Trip"))
        session.execute(
            members.insert(),
            [
                {"group_id": "group-1", "id": "member-2", "name": "Ilaria"},
                {"group_id": "group-1", "id": "member-1", "name": "Satoshi"},
                {"group_id": "group-2", "id": "member-3", "name": "Alex"},
            ],
        )
        session.commit()

    response = client.get("/groups/group-1/members")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": "member-1", "display_name": "Satoshi"},
            {"id": "member-2", "display_name": "Ilaria"},
        ]
    }


def test_lists_no_members_in_existing_group(
    schema_engine: Engine, client: TestClient
) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="group-1", name="Home"))
        session.commit()

    response = client.get("/groups/group-1/members")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_rejects_members_request_for_missing_group(client: TestClient) -> None:
    response = client.get("/groups/missing/members")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_NOT_FOUND"
