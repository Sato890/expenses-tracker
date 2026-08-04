from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .transaction import Transaction


@dataclass(frozen=True)
class Member:
    member_id: str
    name: str = field(compare=False)


@dataclass(frozen=True)
class User:
    user_id: str
    name: str = field(compare=False)


@dataclass
class Group:
    group_id: str
    name: str
    members: list[Member] = field(default_factory=list)
    member_to_user: dict[Member, User] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)
