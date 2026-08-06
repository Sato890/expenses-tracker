from dataclasses import dataclass
from decimal import ROUND_DOWN, Context, Decimal, localcontext

from .group import Member
from .money import Money

ALLOCATION_UNIT = Decimal("1e-18")
CALCULATION_PRECISION = 37


@dataclass(frozen=True)
class Allocation:
    receiver: Member
    amount: Money


def allocate_equally(
    money_to_allocate: Money,
    members: list[Member],
) -> list[Allocation]:
    amount = money_to_allocate.amount
    currency = money_to_allocate.currency
    member_count = len(members)

    calculation_context = Context(prec=CALCULATION_PRECISION, rounding=ROUND_DOWN)

    with localcontext(calculation_context):
        money_per_member = (amount / member_count).quantize(ALLOCATION_UNIT)
        allocated_amount = money_per_member * member_count
        residual_units = int((amount - allocated_amount) / ALLOCATION_UNIT)

        allocations = []

        for index, member in enumerate(members):
            extra_amount = Decimal(0)

            if index < residual_units:
                extra_amount = ALLOCATION_UNIT

            allocation_amount = money_per_member + extra_amount

            allocations.append(
                Allocation(
                    receiver=member,
                    amount=Money(allocation_amount, currency),
                )
            )

    return allocations
