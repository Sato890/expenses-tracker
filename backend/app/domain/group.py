from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Context, Decimal, localcontext
from typing import TYPE_CHECKING

DEBT_CALCULATION_PRECISION = 37

if TYPE_CHECKING:
    from .debt import Debt
    from .transaction import Transaction


@dataclass(frozen=True)
class Member:
    member_id: str
    name: str = field(compare=False)


@dataclass(frozen=True)
class User:
    user_id: str
    name: str = field(compare=False)


@dataclass
class Group:
    group_id: str
    name: str
    members: list[Member] = field(default_factory=list)
    member_to_user: dict[Member, User] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)

    @property
    def debts(self) -> list[Debt]:
        from .debt import calculate_debts
        from .transaction import Expense

        expenses = [
            transaction
            for transaction in self.transactions
            if isinstance(transaction, Expense)
        ]
        return calculate_debts(expenses)

    def calculate_member_settlement_amounts(self) -> dict[Member, Decimal]:
        settlement_amounts = {member: Decimal("0") for member in self.members}

        with localcontext(Context(prec=DEBT_CALCULATION_PRECISION)):
            for debt in self.debts:
                settlement_amounts[debt.debtor] -= debt.amount.amount
                settlement_amounts[debt.creditor] += debt.amount.amount

        return settlement_amounts
