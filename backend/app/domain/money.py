from dataclasses import dataclass
from decimal import ROUND_DOWN, Context, Decimal, localcontext
from types import NotImplementedType

_ALLOCATION_CALCULATION_PRECISION = 37


def _exact_sum_precision(left: Decimal, right: Decimal) -> int:
    lowest_exponent = min(left.as_tuple().exponent, right.as_tuple().exponent)
    highest_digit_position = max(left.adjusted(), right.adjusted())
    aligned_digit_count = highest_digit_position - lowest_exponent + 1
    carry_digit_count = 1
    return aligned_digit_count + carry_digit_count


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        with localcontext(
            Context(prec=_exact_sum_precision(self.amount, other.amount))
        ):
            return Money(
                amount=self.amount + other.amount,
                currency=self.currency,
            )

    def __sub__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, Money):
            return NotImplemented

        with localcontext(
            Context(prec=_exact_sum_precision(self.amount, other.amount))
        ):
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

        with localcontext(Context(prec=_ALLOCATION_CALCULATION_PRECISION)):
            return Money(self.amount * other, self.currency)

    def __truediv__(self, other: object) -> Money | NotImplementedType:
        if not isinstance(other, int):
            return NotImplemented

        with localcontext(Context(prec=_ALLOCATION_CALCULATION_PRECISION)):
            return Money(self.amount / other, self.currency)

    def round_down_to(self, unit: Decimal) -> Money:
        with localcontext(Context(prec=_ALLOCATION_CALCULATION_PRECISION)):
            return Money(self.amount.quantize(unit, rounding=ROUND_DOWN), self.currency)
