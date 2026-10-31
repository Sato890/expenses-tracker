from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import Settings

settings = Settings()

engine = create_engine(str(settings.database_url))


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
