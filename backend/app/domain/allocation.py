from dataclasses import dataclass

from .group import Member
from .money import Money


@dataclass(frozen=True)
class Allocation:
    receiver: Member
    amount: Money
