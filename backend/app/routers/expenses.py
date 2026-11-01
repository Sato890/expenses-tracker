from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.adapters.repository import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyGroupRepository,
)
from app.database import get_session
from app.domain.money import Money
from app.domain.transaction import Expense
from app.services import create_equal_expense

router = APIRouter()


class EqualSplitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["equal"]
    receiver_ids: list[str]


class CreateExpenseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["expense"]
    amount: str
    payer_id: str
    date: date
    category_id: UUID
    split: EqualSplitRequest


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


@router.post(
    "/groups/{group_id}/transactions",
    status_code=status.HTTP_201_CREATED,
    response_model=ExpenseResponse,
)
def create_expense(
    group_id: str,
    request: CreateExpenseRequest,
    session: Annotated[Session, Depends(get_session)],
) -> ExpenseResponse:
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
    return expense_response(group_id, expense)
