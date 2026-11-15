from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.adapters.orm import expenses, group_changes, groups, members
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.settlement_amounts import calculate_expense_balance_changes
from app.domain.transaction import Category, Expense


class AbstractGroupRepository(ABC):
    @abstractmethod
    def record_change(self, group_id: str, entity_type: str, entity_id: str) -> None:
        raise NotImplementedError

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
    def get_member_settlement_amounts(
        self, group_id: str
    ) -> dict[Member, Money] | None:
        raise NotImplementedError

    @abstractmethod
    def get_members_for_expense_creation(self, group_id: str) -> tuple[Member, ...]:
        raise NotImplementedError

    @abstractmethod
    def add_expense(self, group_id: str, expense: Expense) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, group_id: str) -> bool:
        raise NotImplementedError


class SqlAlchemyGroupRepository(AbstractGroupRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, group: Group) -> None:
        self.session.add(group)

    def record_change(self, group_id: str, entity_type: str, entity_id: str) -> None:
        revision = self.session.scalar(
            update(groups)
            .where(groups.c.id == group_id)
            .values(revision=groups.c.revision + 1)
            .returning(groups.c.revision)
        )
        if revision is None:
            raise LookupError(group_id)
        self.session.execute(
            group_changes.insert().values(
                group_id=group_id,
                revision=revision,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )

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

    def get_member_settlement_amounts(
        self, group_id: str
    ) -> dict[Member, Money] | None:
        if not self.exists(group_id):
            return None

        group_members = tuple(
            self.session.scalars(
                select(Member)
                .where(members.c.group_id == group_id)
                .order_by(members.c.id)
            )
        )
        return {member: member.get_settlement_balance() for member in group_members}

    def get_members_for_expense_creation(self, group_id: str) -> tuple[Member, ...]:
        return tuple(
            self.session.scalars(
                select(Member)
                .where(members.c.group_id == group_id)
                .order_by(members.c.id)
            )
        )

    def add_expense(self, group_id: str, expense: Expense) -> None:
        for member, change in calculate_expense_balance_changes(expense).items():
            member.update_settlement_balance(change)
        expense._group_id = group_id
        self.session.add(expense)

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
