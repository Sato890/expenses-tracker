from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from .allocation import Allocation
from .identity import Member
from .money import Money


@dataclass(init=False, unsafe_hash=True)
class Category:
    _id: UUID
    _name: str = field(compare=False)

    def __init__(self, name: str, id: UUID | None = None) -> None:
        self._id = id if id is not None else uuid4()
        self._name = name

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name


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
        allocations: Allocation | Sequence[Allocation],
    ) -> None:
        if isinstance(allocations, Allocation):
            allocations = (allocations,)

        object.__setattr__(self, "expense_id", expense_id)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "payer", payer)
        object.__setattr__(self, "date", date)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "allocations", tuple(allocations))


@dataclass(frozen=True)
class Settlement:
    settlement_id: str
    amount: Money
    payer: Member
    date: date
    receiver: Member


type Transaction = Expense | Settlement
