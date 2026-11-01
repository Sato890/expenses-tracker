import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.adapters.orm import groups, members


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


def test_creates_member_in_group(schema_engine: Engine, client: TestClient) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="group-1", name="Home"))
        session.commit()

    response = client.post("/groups/group-1/members", json={"display_name": "  Aléx  "})

    assert response.status_code == 201
    member = response.json()
    assert member["id"]
    assert member["display_name"] == "Aléx"

    with Session(schema_engine) as session:
        saved = session.execute(
            select(members.c.group_id, members.c.id, members.c.name).where(
                members.c.id == member["id"]
            )
        ).one()
        assert (saved.group_id, saved.id, saved.name) == (
            "group-1",
            member["id"],
            "Aléx",
        )


@pytest.mark.parametrize("name", ["  ", "bad\x00name"])
def test_rejects_invalid_member_name(
    schema_engine: Engine, client: TestClient, name: str
) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="group-1", name="Home"))
        session.commit()

    response = client.post("/groups/group-1/members", json={"display_name": name})

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "INVALID_REQUEST", "message": "Invalid request."}
    }

    with Session(schema_engine) as session:
        assert session.scalars(select(members.c.id)).all() == []


def test_rejects_unknown_member_field(
    schema_engine: Engine, client: TestClient
) -> None:
    with Session(schema_engine) as session:
        session.execute(groups.insert().values(id="group-1", name="Home"))
        session.commit()

    response = client.post(
        "/groups/group-1/members",
        json={"display_name": "Alex", "account_id": "user-1"},
    )

    assert response.status_code == 422


def test_rejects_member_creation_for_missing_group(client: TestClient) -> None:
    response = client.post("/groups/missing/members", json={"display_name": "Alex"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_NOT_FOUND"
