from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from .allocation import Allocation
from .group import Member
from .money import Money


class TransactionType(StrEnum):
    EXPENSE = "expense"
    SETTLEMENT = "settlement"


@dataclass(frozen=True)
class Category:
    name: str


@dataclass(frozen=True)
class Transaction:
    transaction_type: TransactionType
    amount: Money
    payer: Member
    date: date
    allocations: tuple[Allocation, ...] = ()
    receiver: Member | None = None
    category: Category | None = None
