"""Persistence access for groups and categories; callers own the transaction."""

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.group import Group
from app.domain.transaction import Category


class AbstractGroupRepository(ABC):
    @abstractmethod
    def add(self, group: Group) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, group_id: str) -> Group | None:
        raise NotImplementedError


class SqlAlchemyGroupRepository(AbstractGroupRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, group: Group) -> None:
        self.session.add(group)

    def get(self, group_id: str) -> Group | None:
        return self.session.get(Group, group_id)


class AbstractCategoryRepository(ABC):
    @abstractmethod
    def get(self, category_id: UUID) -> Category | None:
        raise NotImplementedError


class SqlAlchemyCategoryRepository(AbstractCategoryRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, category_id: UUID) -> Category | None:
        return self.session.get(Category, category_id)
