from uuid import uuid4

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.adapters.orm import mapper_registry, metadata, start_mappers
from app.adapters.repository import SqlAlchemyGroupRepository
from app.config import ENV_FILE
from app.domain.group import Group
from app.domain.identity import Member


class IntegrationDatabaseSettings(BaseSettings):
    test_database_url: PostgresDsn

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, dotenv_filtering="only_existing"
    )


def test_reconstructs_group_and_members_in_a_fresh_session() -> None:
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
        group = Group(
            "group-1",
            "Household",
            _members=[
                Member("member-1", "Satoshi"),
                Member("member-2", "Ilaria"),
            ],
        )

        with Session(schema_engine) as session:
            SqlAlchemyGroupRepository(session).add(group)
            session.commit()

        with Session(schema_engine) as session:
            loaded = SqlAlchemyGroupRepository(session).get("group-1")

            assert loaded is not None
            assert loaded.name == "Household"
            assert loaded.members == (
                Member("member-1", "Satoshi"),
                Member("member-2", "Ilaria"),
            )
    finally:
        mapper_registry.dispose()
        schema_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()
