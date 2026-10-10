from dataclasses import dataclass
from decimal import Decimal

CALCULATION_PRECISION = 37


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise NotImplementedError

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency,
        )

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise NotImplementedError

        return Money(
            amount=self.amount - other.amount,
            currency=self.currency,
        )
