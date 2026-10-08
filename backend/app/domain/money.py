from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise NotImplementedError

        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency,
        )
