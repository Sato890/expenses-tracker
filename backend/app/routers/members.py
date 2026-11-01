from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.orm import groups, members
from app.database import get_session

router = APIRouter()


class CreateMember(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1)


@router.get("/groups/{group_id}/members", response_model=None)
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


@router.post(
    "/groups/{group_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
)
def create_member(
    group_id: str,
    member: CreateMember,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str] | JSONResponse:
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

    member_id = uuid4().hex

    session.execute(
        members.insert().values(
            group_id=group_id, id=member_id, name=member.display_name
        )
    )
    session.commit()
    return {"id": member_id, "display_name": member.display_name}
