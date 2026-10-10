from dataclasses import dataclass
from decimal import Context, localcontext

from .group import Member
from .money import CALCULATION_PRECISION, Money
from .transaction import Expense


@dataclass(frozen=True)
class Debt:
    amount: Money
    debtor: Member
    creditor: Member

    def __add__(self, other: Debt) -> Debt:
        if not isinstance(other, Debt):
            raise NotImplementedError

        if not self.has_same_direction_as(other):
            raise ValueError("Can only add debts in the same direction")

        return Debt(self.amount + other.amount, self.debtor, self.creditor)

    def __sub__(self, other: Debt) -> Debt | None:
        if not isinstance(other, Debt):
            raise NotImplementedError

        if not self.is_opposite_of(other):
            raise ValueError(
                "Can only subtract opposite debts between the same members"
            )

        difference = self.amount - other.amount

        if difference.amount > 0:
            return Debt(difference, self.debtor, self.creditor)
        elif difference.amount < 0:
            return Debt(
                Money(-difference.amount, difference.currency),
                other.debtor,
                other.creditor,
            )
        else:
            return None

    def has_same_direction_as(self, other: Debt) -> bool:
        return self.debtor == other.debtor and self.creditor == other.creditor

    def is_opposite_of(self, other: Debt) -> bool:
        return self.debtor == other.creditor and self.creditor == other.debtor


def calculate_expense_debts(expense: Expense) -> list[Debt]:
    debts = []

    for allocation in expense.allocations:
        if allocation.receiver == expense.payer:
            continue

        debt = Debt(allocation.share, allocation.receiver, expense.payer)
        debts.append(debt)

    return debts


def calculate_debts(expenses: list[Expense]) -> list[Debt]:
    debts_by_members: dict[frozenset[Member], Debt] = {}

    with localcontext(Context(prec=CALCULATION_PRECISION)):
        for expense in expenses:
            for expense_debt in calculate_expense_debts(expense):
                member_pair = _get_member_pair(expense_debt)
                debt = debts_by_members.get(member_pair)

                if debt is None:
                    debts_by_members[member_pair] = expense_debt
                    continue

                net_debt = _get_net_debts(debt, expense_debt)

                if net_debt is None:
                    del debts_by_members[member_pair]
                else:
                    debts_by_members[member_pair] = net_debt

    return list(debts_by_members.values())


def _get_member_pair(debt: Debt) -> frozenset[Member]:
    return frozenset((debt.debtor, debt.creditor))


def _get_net_debts(debt: Debt, other_debt: Debt) -> Debt | None:
    if debt.has_same_direction_as(other_debt):
        return debt + other_debt

    return debt - other_debt
