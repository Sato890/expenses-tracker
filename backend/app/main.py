from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.orm import groups
from app.database import get_session

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/groups")
def list_groups(
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, str]]:
    return [
        {"id": row.id, "name": row.name}
        for row in session.execute(select(groups.c.id, groups.c.name)).all()
    ]
