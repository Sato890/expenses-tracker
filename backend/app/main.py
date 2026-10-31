from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.orm import categories, groups, members
from app.database import get_session

app = FastAPI()


class CreateGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)


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


@app.post("/groups", status_code=status.HTTP_201_CREATED)
def create_group(
    group: CreateGroup,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    group_id = uuid4().hex
    session.execute(groups.insert().values(id=group_id, name=group.name))
    session.commit()
    return {"id": group_id, "name": group.name}


@app.get("/groups/{group_id}/members", response_model=None)
def list_members(
    group_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, list[dict[str, str]]] | JSONResponse:
    group_exists = session.execute(
        select(groups.c.id).where(groups.c.id == group_id)
    ).scalar_one_or_none()
    if group_exists is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {"code": "GROUP_NOT_FOUND", "message": "Group not found."}
            },
        )

    return {
        "items": [
            {"id": row.id, "display_name": row.name}
            for row in session.execute(
                select(members.c.id, members.c.name)
                .where(members.c.group_id == group_id)
                .order_by(members.c.id)
            ).all()
        ]
    }


@app.get("/categories")
def list_categories(
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, list[dict[str, str]]]:
    return {
        "items": [
            {"id": str(row.id), "name": row.name}
            for row in session.execute(
                select(categories.c.id, categories.c.name).order_by(categories.c.name)
            ).all()
        ]
    }
