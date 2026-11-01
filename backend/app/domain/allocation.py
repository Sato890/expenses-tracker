from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from .identity import Member
from .money import Money

ALLOCATION_UNIT = Decimal("1e-18")


@dataclass(init=False, unsafe_hash=True)
class Allocation:
    _receiver: Member
    _share: Money

    def __init__(self, receiver: Member, share: Money) -> None:
        self._receiver = receiver
        self._share = share

    @property
    def receiver(self) -> Member:
        return self._receiver

    @property
    def share(self) -> Money:
        return self._share


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

    receiver_ids: set[str] = set()
    for allocation in allocations:
        if allocation.share.amount <= 0:
            raise ValueError("Allocation shares must be positive")
        if allocation.receiver.id in receiver_ids:
            raise ValueError("Allocation receivers must be unique")
        receiver_ids.add(allocation.receiver.id)

    total = Money(Decimal("0"), expected_total.currency)
    for allocation in allocations:
        total += allocation.share

    if total != expected_total:
        raise ValueError("The allocations must add up to the total")
