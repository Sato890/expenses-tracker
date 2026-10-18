from dataclasses import dataclass
from decimal import ROUND_DOWN, Context, Decimal, localcontext
from types import NotImplementedType

# Up to 18 integer digits, 18 fractional digits, and one guard digit.
CALCULATION_PRECISION = 37


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        with localcontext(Context(prec=CALCULATION_PRECISION)):
            return Money(
                amount=self.amount + other.amount,
                currency=self.currency,
            )

    def __sub__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        with localcontext(Context(prec=CALCULATION_PRECISION)):
            return Money(
                amount=self.amount - other.amount,
                currency=self.currency,
            )

    def __neg__(self) -> Money:
        return Money(self.amount.copy_negate(), self.currency)

    def __lt__(self, other: object) -> bool | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        return self.amount < other.amount

    def __mul__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, int):
            return NotImplemented

        with localcontext(Context(prec=CALCULATION_PRECISION)):
            return Money(self.amount * other, self.currency)

    def __truediv__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, int):
            return NotImplemented

        with localcontext(Context(prec=CALCULATION_PRECISION)):
            return Money(self.amount / other, self.currency)

    def round_down_to(self, unit: Decimal) -> Money:
        with localcontext(Context(prec=CALCULATION_PRECISION)):
            return Money(self.amount.quantize(unit, rounding=ROUND_DOWN), self.currency)
