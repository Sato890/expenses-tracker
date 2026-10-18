from dataclasses import dataclass
from datetime import date

from .allocation import Allocation
from .identity import Member
from .money import Money


@dataclass(frozen=True)
class Category:
    name: str


@dataclass(frozen=True, init=False)
class Expense:
    expense_id: str
    amount: Money
    payer: Member
    date: date
    category: Category
    allocations: tuple[Allocation, ...]

    def __init__(
        self,
        expense_id: str,
        amount: Money,
        payer: Member,
        date: date,
        category: Category,
        allocations: Allocation | tuple[Allocation, ...],
    ) -> None:
        if isinstance(allocations, Allocation):
            allocations = (allocations,)

        object.__setattr__(self, "expense_id", expense_id)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "payer", payer)
        object.__setattr__(self, "date", date)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "allocations", allocations)


@dataclass(frozen=True)
class Settlement:
    settlement_id: str
    amount: Money
    payer: Member
    date: date
    receiver: Member


type Transaction = Expense | Settlement
