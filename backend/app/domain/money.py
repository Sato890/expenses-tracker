from dataclasses import dataclass
from decimal import Decimal
from types import NotImplementedType

CALCULATION_PRECISION = 37


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency,
        )

    def __sub__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        return Money(
            amount=self.amount - other.amount,
            currency=self.currency,
        )
