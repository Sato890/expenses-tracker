from dataclasses import dataclass, field
from decimal import Decimal

from .money import Money


@dataclass(init=False, unsafe_hash=True)
class Member:
    _id: str
    _name: str = field(compare=False)
    _settlement_balance_value: Decimal = field(compare=False)

    def __init__(self, id: str, name: str) -> None:
        self._id = id
        self._name = name
        self._settlement_balance_value = Decimal("0")

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def get_settlement_balance(self) -> Money:
        return Money(self._settlement_balance_value, "EUR")

    def update_settlement_balance(self, change: Money) -> None:
        self._settlement_balance_value = (self.get_settlement_balance() + change).amount


@dataclass(frozen=True)
class User:
    id: str
    name: str = field(compare=False)
