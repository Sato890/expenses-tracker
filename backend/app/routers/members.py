from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.orm import groups, members
from app.api_errors import error_response
from app.database import get_session

router = APIRouter()


class CreateMember(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1)

    @field_validator("display_name")
    @classmethod
    def name_contains_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Names must not contain NUL characters")
        return value


class MemberResponse(BaseModel):
    id: str
    display_name: str


class MemberListResponse(BaseModel):
    items: list[MemberResponse]


@router.get("/groups/{group_id}/members", response_model=MemberListResponse)
def list_members(
    group_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> MemberListResponse | JSONResponse:
    group_exists = session.execute(
        select(groups.c.id).where(groups.c.id == group_id)
    ).scalar_one_or_none()
    if group_exists is None:
        return error_response(404, "GROUP_NOT_FOUND", "Group not found.")

    return MemberListResponse(
        items=[
            MemberResponse(id=row.id, display_name=row.name)
            for row in session.execute(
                select(members.c.id, members.c.name)
                .where(members.c.group_id == group_id)
                .order_by(members.c.id)
            ).all()
        ]
    )


@router.post(
    "/groups/{group_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberResponse,
)
def create_member(
    group_id: str,
    member: CreateMember,
    session: Annotated[Session, Depends(get_session)],
) -> MemberResponse | JSONResponse:
    group_exists = session.execute(
        select(groups.c.id).where(groups.c.id == group_id)
    ).scalar_one_or_none()
    if group_exists is None:
        return error_response(404, "GROUP_NOT_FOUND", "Group not found.")

    member_id = uuid4().hex

    session.execute(
        members.insert().values(
            group_id=group_id, id=member_id, name=member.display_name
        )
    )
    session.commit()
    return MemberResponse(id=member_id, display_name=member.display_name)
