import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.adapters.repository import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyExpenseRepository,
    SqlAlchemyGroupRepository,
)
from app.api_errors import error_response
from app.database import get_session
from app.domain.money import Money
from app.domain.transaction import Expense
from app.services import (
    GroupNotFoundError,
    InvalidCategoryError,
    InvalidParticipantError,
    create_equal_expense,
    list_group_expenses,
)

router = APIRouter()


class EqualSplitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["equal"]
    receiver_ids: list[str]


class CreateExpenseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["expense"]
    amount: str = Field(max_length=18, pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    payer_id: str
    date: date
    category_id: UUID
    split: EqualSplitRequest

    @field_validator("amount")
    @classmethod
    def amount_is_positive(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("The expense amount must be positive")
        return value

    @field_validator("date", mode="before")
    @classmethod
    def date_uses_iso_format(cls, value: object) -> object:
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
        ):
            raise ValueError("The date must use YYYY-MM-DD")
        return value


class AllocationResponse(BaseModel):
    receiver_id: str
    amount: str


class ExpenseResponse(BaseModel):
    id: str
    group_id: str
    type: Literal["expense"]
    amount: str
    currency: str
    payer_id: str
    date: date
    category_id: UUID
    allocations: list[AllocationResponse]


class ExpenseHistoryResponse(BaseModel):
    items: list[ExpenseResponse]
    limit: int
    offset: int


def expense_response(group_id: str, expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.expense_id,
        group_id=group_id,
        type="expense",
        amount=str(expense.amount.amount),
        currency=expense.amount.currency,
        payer_id=expense.payer.id,
        date=expense.date,
        category_id=expense.category.id,
        allocations=[
            AllocationResponse(
                receiver_id=allocation.receiver.id,
                amount=str(allocation.share.amount),
            )
            for allocation in expense.allocations
        ],
    )


@router.get("/groups/{group_id}/transactions", response_model=ExpenseHistoryResponse)
def list_expenses(
    group_id: str,
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExpenseHistoryResponse | JSONResponse:
    try:
        items = list_group_expenses(
            group_id,
            limit,
            offset,
            SqlAlchemyGroupRepository(session),
            SqlAlchemyExpenseRepository(session),
        )
    except GroupNotFoundError:
        return error_response(404, "GROUP_NOT_FOUND", "Group not found.")
    return ExpenseHistoryResponse(
        items=[expense_response(group_id, expense) for expense in items],
        limit=limit,
        offset=offset,
    )


@router.post(
    "/groups/{group_id}/transactions",
    status_code=status.HTTP_201_CREATED,
    response_model=ExpenseResponse,
)
def create_expense(
    group_id: str,
    request: CreateExpenseRequest,
    session: Annotated[Session, Depends(get_session)],
) -> ExpenseResponse | JSONResponse:
    try:
        expense = create_equal_expense(
            group_id,
            Money(Decimal(request.amount), "EUR"),
            request.payer_id,
            request.date,
            request.category_id,
            request.split.receiver_ids,
            SqlAlchemyGroupRepository(session),
            SqlAlchemyCategoryRepository(session),
            session,
        )
    except GroupNotFoundError:
        return error_response(404, "GROUP_NOT_FOUND", "Group not found.")
    except InvalidCategoryError:
        return error_response(422, "INVALID_CATEGORY", "Invalid category.")
    except InvalidParticipantError:
        return error_response(
            422,
            "INVALID_PARTICIPANT",
            "A selected participant does not belong to this group.",
        )
    except ValueError:
        return error_response(422, "INVALID_REQUEST", "Invalid request.")

    return expense_response(group_id, expense)
