from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from .identity import Member
from .money import Money

ALLOCATION_UNIT = Decimal("1e-18")


@dataclass(frozen=True)
class Allocation:
    receiver: Member
    share: Money


def allocate_equally(
    money_to_allocate: Money,
    members: list[Member],
) -> tuple[Allocation, ...]:
    member_count = len(members)
    money_per_member = (money_to_allocate / member_count).round_down_to(ALLOCATION_UNIT)
    remainder = money_to_allocate - money_per_member * member_count
    extra_unit = Money(ALLOCATION_UNIT, money_to_allocate.currency)
    allocations = []

    for member in members:
        share = money_per_member
        if remainder.amount >= ALLOCATION_UNIT:
            share += extra_unit
            remainder -= extra_unit

        allocations.append(Allocation(receiver=member, share=share))

    return tuple(allocations)


def validate_exact_allocations(
    expected_total: Money,
    allocations: Sequence[Allocation],
) -> None:
    if expected_total.amount <= 0:
        raise ValueError("The expense amount must be positive")

    if not allocations:
        raise ValueError("At least one allocation is required")

    for allocation in allocations:
        if allocation.share.amount <= 0:
            raise ValueError("Allocation shares must be positive")

    total = Money(Decimal("0"), expected_total.currency)
    for allocation in allocations:
        total += allocation.share

    if total != expected_total:
        raise ValueError("The allocations must add up to the total")
