from dataclasses import dataclass

from .group import Member
from .money import Money


@dataclass(frozen=True)
class Debt:
    amount: Money
    debtor: Member
    creditor: Member
