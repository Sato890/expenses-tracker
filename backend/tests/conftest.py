from collections.abc import Iterator
from uuid import uuid4

import pytest
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.adapters.orm import mapper_registry, metadata, start_mappers
from app.config import ENV_FILE


class IntegrationDatabaseSettings(BaseSettings):
    test_database_url: PostgresDsn

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, dotenv_filtering="only_existing"
    )


@pytest.fixture
def schema_engine() -> Iterator[Engine]:
    database_url = str(IntegrationDatabaseSettings().test_database_url)

    schema = f"test_{uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(CreateSchema(schema))

    schema_engine = create_engine(
        database_url,
        connect_args={"options": f"-csearch_path={schema}"},
    )

    try:
        metadata.create_all(schema_engine)
        start_mappers()
        yield schema_engine
    finally:
        mapper_registry.dispose()
        schema_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()
