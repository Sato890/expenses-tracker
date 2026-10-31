from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import app


@pytest.fixture
def client(schema_engine: Engine) -> Iterator[TestClient]:
    def test_session() -> Iterator[Session]:
        with Session(schema_engine) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
