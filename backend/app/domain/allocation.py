from dataclasses import dataclass
from decimal import ROUND_DOWN, Context, Decimal, localcontext

from .group import Member
from .money import CALCULATION_PRECISION, Money

ALLOCATION_UNIT = Decimal("1e-18")


@dataclass(frozen=True)
class Allocation:
    receiver: Member
    share: Money


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
                    share=Money(allocation_amount, currency),
                )
            )

    return allocations


def validate_exact_allocations(
    expected_total: Money,
    allocations: list[Allocation],
) -> None:
    if expected_total.amount <= 0:
        raise ValueError("The expense amount must be positive")

    if not allocations:
        raise ValueError("At least one allocation is required")

    for allocation in allocations:
        if allocation.share.amount <= 0:
            raise ValueError("Allocation shares must be positive")

    calculation_context = Context(prec=CALCULATION_PRECISION, rounding=ROUND_DOWN)

    with localcontext(calculation_context):
        total = Decimal("0")
        for allocation in allocations:
            total += allocation.share.amount

    if total != expected_total.amount:
        raise ValueError("The allocations must add up to the total")
