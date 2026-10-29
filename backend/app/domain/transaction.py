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


@dataclass(init=False, unsafe_hash=True)
class Expense:
    _expense_id: str
    _amount: Money
    _payer: Member
    _date: date
    _category: Category
    _allocations: list[Allocation] = field(hash=False)

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

        self._expense_id = expense_id
        self._amount = amount
        self._payer = payer
        self._date = date
        self._category = category
        self._allocations = sorted(allocations, key=lambda item: item.receiver.id)

    @property
    def expense_id(self) -> str:
        return self._expense_id

    @property
    def amount(self) -> Money:
        return self._amount

    @property
    def payer(self) -> Member:
        return self._payer

    @property
    def date(self) -> date:
        return self._date

    @property
    def category(self) -> Category:
        return self._category

    @property
    def allocations(self) -> tuple[Allocation, ...]:
        return tuple(self._allocations)


@dataclass(frozen=True)
class Settlement:
    settlement_id: str
    amount: Money
    payer: Member
    date: date
    receiver: Member


type Transaction = Expense | Settlement
