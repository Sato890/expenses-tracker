from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.repository import SqlAlchemyGroupRepository
from app.api_errors import error_response
from app.database import get_session
from app.services import GroupNotFoundError, get_group_settlement_amounts

router = APIRouter()


class MemberSettlementAmount(BaseModel):
    member_id: str
    amount: str


class SettlementAmountsResponse(BaseModel):
    group_id: str
    currency: str
    items: list[MemberSettlementAmount]


@router.get(
    "/groups/{group_id}/settlement-amounts", response_model=SettlementAmountsResponse
)
def read_settlement_amounts(
    group_id: str, session: Annotated[Session, Depends(get_session)]
) -> SettlementAmountsResponse | JSONResponse:
    try:
        amounts = get_group_settlement_amounts(
            group_id, SqlAlchemyGroupRepository(session)
        )
    except GroupNotFoundError:
        return error_response(404, "GROUP_NOT_FOUND", "Group not found.")

    return SettlementAmountsResponse(
        group_id=group_id,
        currency="EUR",
        items=[
            MemberSettlementAmount(member_id=member.id, amount=str(amount.amount))
            for member, amount in sorted(amounts.items(), key=lambda item: item[0].id)
        ],
    )
