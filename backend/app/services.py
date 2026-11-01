"""Application operations that coordinate domain behavior and persistence."""

from datetime import date
from typing import Protocol
from uuid import UUID, uuid4

from app.adapters.repository import (
    AbstractCategoryRepository,
    AbstractExpenseRepository,
    AbstractGroupRepository,
)
from app.domain.allocation import allocate_equally
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Expense


class SessionLike(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class GroupNotFoundError(LookupError):
    pass


class InvalidCategoryError(ValueError):
    pass


class InvalidParticipantError(ValueError):
    pass


class InvalidExpenseRequestError(ValueError):
    pass


def get_group_settlement_amounts(
    group_id: str, groups: AbstractGroupRepository
) -> dict[Member, Money]:
    group = groups.get(group_id)
    if group is None:
        raise GroupNotFoundError(group_id)
    return group.calculate_member_settlement_amounts()


def list_group_expenses(
    group_id: str,
    limit: int,
    offset: int,
    groups: AbstractGroupRepository,
    expenses: AbstractExpenseRepository,
) -> list[Expense]:
    if not groups.exists(group_id):
        raise GroupNotFoundError(group_id)
    return expenses.list_by_group_id(group_id, limit, offset)


def create_equal_expense(
    group_id: str,
    amount: Money,
    payer_id: str,
    expense_date: date,
    category_id: UUID,
    receiver_ids: list[str],
    groups: AbstractGroupRepository,
    categories: AbstractCategoryRepository,
    session: SessionLike,
) -> Expense:
    try:
        group = groups.get(group_id)
        if group is None:
            raise GroupNotFoundError(group_id)

        category = categories.get(category_id)
        if category is None:
            raise InvalidCategoryError(category_id)

        if amount.amount <= 0:
            raise InvalidExpenseRequestError("The expense amount must be positive")
        if not receiver_ids:
            raise InvalidExpenseRequestError("At least one receiver is required")
        if len(receiver_ids) != len(set(receiver_ids)):
            raise InvalidExpenseRequestError("Receiver IDs must be unique")

        members = {member.id: member for member in group.members}
        if payer_id not in members or any(
            receiver_id not in members for receiver_id in receiver_ids
        ):
            raise InvalidParticipantError("A selected participant is not in the group")

        expense = Expense(
            expense_id=uuid4().hex,
            amount=amount,
            payer=members[payer_id],
            date=expense_date,
            category=category,
            allocations=allocate_equally(
                amount, [members[receiver_id] for receiver_id in receiver_ids]
            ),
        )
        group.add_expense(expense)
        session.commit()
        return expense
    except Exception:
        session.rollback()
        raise
