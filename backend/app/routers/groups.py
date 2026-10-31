from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.orm import groups
from app.database import get_session

router = APIRouter()


class CreateGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)


@router.get("/groups")
def list_groups(
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, str]]:
    return [
        {"id": row.id, "name": row.name}
        for row in session.execute(
            select(groups.c.id, groups.c.name).order_by(groups.c.name, groups.c.id)
        ).all()
    ]


@router.post("/groups", status_code=status.HTTP_201_CREATED)
def create_group(
    group: CreateGroup,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    group_id = uuid4().hex

    session.execute(groups.insert().values(id=group_id, name=group.name))
    session.commit()
    return {"id": group_id, "name": group.name}
