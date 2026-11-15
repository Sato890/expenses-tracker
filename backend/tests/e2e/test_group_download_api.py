import gzip
import json
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.adapters.orm import allocations, categories, expenses, groups, members
from app.main import app
from app.routers import download as download_routes
from app.routers.download import download_group

CATEGORY_ID = UUID("0bacd5bc-13a0-430e-a8b3-1dbf69194e8b")


def prepare_group(engine: Engine) -> None:
    with Session(engine) as session:
        session.execute(groups.insert().values(id="home", name="Home"))
        session.execute(groups.insert().values(id="trip", name="Trip"))
        session.execute(
            members.insert(),
            [
                {"group_id": "home", "id": "alex", "name": "Alex"},
                {"group_id": "home", "id": "bea", "name": "Bea"},
                {"group_id": "home", "id": "cam", "name": "Cam"},
                {"group_id": "trip", "id": "other", "name": "Other"},
            ],
        )
        session.execute(categories.insert().values(id=CATEGORY_ID, name="Groceries"))
        session.commit()


def expense_request() -> dict[str, object]:
    return {
        "type": "expense",
        "amount": "10",
        "payer_id": "alex",
        "date": "2026-11-15",
        "category_id": str(CATEGORY_ID),
        "split": {"type": "equal", "receiver_ids": ["bea", "alex", "cam"]},
    }


def test_empty_download_and_conditional_request_check_group_existence(
    schema_engine: Engine, client: TestClient
) -> None:
    prepare_group(schema_engine)

    first = client.get("/groups/home/download")
    assert first.status_code == 200
    assert first.headers["etag"]
    assert first.json() == {
        "group": {"id": "home", "name": "Home"},
        "members": [
            {"id": "alex", "display_name": "Alex"},
            {"id": "bea", "display_name": "Bea"},
            {"id": "cam", "display_name": "Cam"},
        ],
        "categories": [],
        "transactions": [],
        "settlement_amounts": {
            "group_id": "home",
            "currency": "EUR",
            "items": [
                {"member_id": "alex", "amount": "0"},
                {"member_id": "bea", "amount": "0"},
                {"member_id": "cam", "amount": "0"},
            ],
        },
        "transaction_count": 0,
        "sync_token": first.headers["etag"].strip('"'),
    }

    statements: list[str] = []

    def record_sql(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(schema_engine, "before_cursor_execute", record_sql)
    try:
        unchanged = client.get(
            "/groups/home/download", headers={"If-None-Match": first.headers["etag"]}
        )
    finally:
        event.remove(schema_engine, "before_cursor_execute", record_sql)
    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert unchanged.headers["etag"] == first.headers["etag"]
    assert not any("FROM expenses" in statement for statement in statements)

    missing = client.get(
        "/groups/missing/download", headers={"If-None-Match": first.headers["etag"]}
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "GROUP_NOT_FOUND"

    added = client.post("/groups/home/members", json={"display_name": "Dana"})
    assert added.status_code == 201
    changed = client.get(
        "/groups/home/download", headers={"If-None-Match": first.headers["etag"]}
    )
    assert changed.status_code == 200
    assert changed.headers["etag"] != first.headers["etag"]
    assert added.json() in changed.json()["members"]
    assert changed.json()["transaction_count"] == 0


def test_changed_download_contains_every_expense_and_precise_shares(
    schema_engine: Engine, client: TestClient
) -> None:
    prepare_group(schema_engine)
    old_tag = client.get("/groups/home/download").headers["etag"]
    created = client.post("/groups/home/transactions", json=expense_request())
    assert created.status_code == 201

    with Session(schema_engine) as session:
        session.execute(
            expenses.insert(),
            [
                {
                    "group_id": "home",
                    "id": f"bulk-{index:03d}",
                    "amount": Decimal("1"),
                    "currency": "EUR",
                    "payer_id": "alex",
                    "date": date(2026, 11, 14),
                    "category_id": CATEGORY_ID,
                }
                for index in range(101)
            ],
        )
        session.execute(
            allocations.insert(),
            [
                {
                    "group_id": "home",
                    "expense_id": f"bulk-{index:03d}",
                    "receiver_id": "alex",
                    "amount": Decimal("1"),
                    "currency": "EUR",
                }
                for index in range(101)
            ],
        )
        session.execute(
            expenses.insert().values(
                group_id="trip",
                id="trip-only",
                amount=Decimal("2"),
                currency="EUR",
                payer_id="other",
                date=date(2026, 11, 15),
                category_id=CATEGORY_ID,
            )
        )
        session.execute(
            allocations.insert().values(
                group_id="trip",
                expense_id="trip-only",
                receiver_id="other",
                amount=Decimal("2"),
                currency="EUR",
            )
        )
        session.commit()

    response = client.get("/groups/home/download", headers={"If-None-Match": old_tag})
    assert response.status_code == 200
    assert response.headers["etag"] != old_tag
    body = response.json()
    assert body["transaction_count"] == 102
    assert len(body["transactions"]) == 102
    assert body["transactions"][0] == created.json()
    assert body["transactions"][0]["allocations"] == [
        {"receiver_id": "alex", "amount": "3.333333333333333333"},
        {"receiver_id": "bea", "amount": "3.333333333333333334"},
        {"receiver_id": "cam", "amount": "3.333333333333333333"},
    ]
    assert body["categories"] == [{"id": str(CATEGORY_ID), "name": "Groceries"}]
    assert "trip-only" not in {item["id"] for item in body["transactions"]}
    assert body["settlement_amounts"]["items"] == [
        {"member_id": "alex", "amount": "6.666666666666666667"},
        {"member_id": "bea", "amount": "-3.333333333333333334"},
        {"member_id": "cam", "amount": "-3.333333333333333333"},
    ]


def test_download_stays_at_one_revision_when_a_writer_commits_between_queries(
    schema_engine: Engine, client: TestClient
) -> None:
    prepare_group(schema_engine)
    wrote = False

    def write_after_revision_read(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        nonlocal wrote
        if wrote or "count(" not in statement.lower() or "expenses" not in statement:
            return
        wrote = True
        with Session(schema_engine) as writer:
            writer.execute(
                expenses.insert().values(
                    group_id="home",
                    id="newer",
                    amount=Decimal("1"),
                    currency="EUR",
                    payer_id="alex",
                    date=date(2026, 11, 15),
                    category_id=CATEGORY_ID,
                )
            )
            writer.execute(
                allocations.insert().values(
                    group_id="home",
                    expense_id="newer",
                    receiver_id="alex",
                    amount=Decimal("1"),
                    currency="EUR",
                )
            )
            writer.execute(
                groups.update().where(groups.c.id == "home").values(revision=1)
            )
            writer.commit()

    event.listen(schema_engine, "before_cursor_execute", write_after_revision_read)
    try:
        old = client.get("/groups/home/download")
    finally:
        event.remove(schema_engine, "before_cursor_execute", write_after_revision_read)

    assert wrote
    assert old.status_code == 200
    assert old.json()["transaction_count"] == 0
    assert old.json()["transactions"] == []
    current = client.get("/groups/home/download")
    assert current.status_code == 200
    assert current.json()["transaction_count"] == 1
    assert current.headers["etag"] != old.headers["etag"]


def test_download_sends_real_gzip_bytes(schema_engine: Engine) -> None:
    prepare_group(schema_engine)
    request = Request({"type": "http", "headers": [(b"accept-encoding", b"gzip")]})
    with Session(schema_engine) as session:
        response = download_group("home", request, session)
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert json.loads(gzip.decompress(response.body))["group"] == {
        "id": "home",
        "name": "Home",
    }


def test_failed_materialization_returns_an_error_without_a_partial_copy(
    schema_engine: Engine, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_group(schema_engine)

    def fail_materialization(_group: object, _count: int, _token: str) -> None:
        raise RuntimeError("Download failed")

    monkeypatch.setattr(download_routes, "_download_body", fail_materialization)
    with TestClient(app, raise_server_exceptions=False) as error_client:
        response = error_client.get("/groups/home/download")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Internal server error."}
    }
