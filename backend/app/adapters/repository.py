"""Collection-like access to groups; callers own the transaction."""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.domain.group import Group


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
