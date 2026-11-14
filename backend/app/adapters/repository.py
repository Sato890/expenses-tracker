from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.orm import expenses, groups, members
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.transaction import Category, Expense


class AbstractGroupRepository(ABC):
    @abstractmethod
    def count_transactions_for_update(self, group_id: str) -> int | None:
        raise NotImplementedError

    @abstractmethod
    def add(self, group: Group) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, group_id: str) -> Group | None:
        raise NotImplementedError

    @abstractmethod
    def get_members_for_expense_creation(self, group_id: str) -> tuple[Member, ...]:
        raise NotImplementedError

    @abstractmethod
    def exists(self, group_id: str) -> bool:
        raise NotImplementedError


class SqlAlchemyGroupRepository(AbstractGroupRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, group: Group) -> None:
        self.session.add(group)

    def count_transactions_for_update(self, group_id: str) -> int | None:
        group = self.session.scalar(
            select(groups.c.id).where(groups.c.id == group_id).with_for_update()
        )
        if group is None:
            return None
        return self.session.scalar(
            select(func.count())
            .select_from(expenses)
            .where(expenses.c.group_id == group_id)
        )

    def get(self, group_id: str) -> Group | None:
        return self.session.get(Group, group_id)

    def get_members_for_expense_creation(self, group_id: str) -> tuple[Member, ...]:
        return tuple(
            self.session.scalars(
                select(Member)
                .where(members.c.group_id == group_id)
                .order_by(members.c.id)
            )
        )

    def exists(self, group_id: str) -> bool:
        return (
            self.session.scalar(select(groups.c.id).where(groups.c.id == group_id))
            is not None
        )


class AbstractExpenseRepository(ABC):
    @abstractmethod
    def list_by_group_id(self, group_id: str, limit: int, offset: int) -> list[Expense]:
        raise NotImplementedError


class SqlAlchemyExpenseRepository(AbstractExpenseRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_group_id(self, group_id: str, limit: int, offset: int) -> list[Expense]:
        return list(
            self.session.scalars(
                select(Expense)
                .where(expenses.c.group_id == group_id)
                .order_by(expenses.c.date.desc(), expenses.c.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )


class AbstractCategoryRepository(ABC):
    @abstractmethod
    def get(self, category_id: UUID) -> Category | None:
        raise NotImplementedError


class SqlAlchemyCategoryRepository(AbstractCategoryRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, category_id: UUID) -> Category | None:
        return self.session.get(Category, category_id)
