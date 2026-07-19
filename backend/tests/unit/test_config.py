import pytest
from pydantic import ValidationError

from app.config import Settings

VALID_DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/database"


def test_loads_database_url_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)

    settings = Settings(_env_file=None)

    assert str(settings.database_url) == VALID_DATABASE_URL


def test_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_invalid_database_url() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="test_invalid_format")
