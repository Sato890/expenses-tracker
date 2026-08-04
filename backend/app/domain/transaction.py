from dataclasses import dataclass
from datetime import date

from .allocation import Allocation
from .group import Member
from .money import Money


@dataclass(frozen=True)
class Category:
    name: str


@dataclass(frozen=True)
class Expense:
    amount: Money
    payer: Member
    date: date
    category: Category
    allocations: tuple[Allocation, ...]


@dataclass(frozen=True)
class Settlement:
    amount: Money
    payer: Member
    date: date
    receiver: Member


type Transaction = Expense | Settlement
