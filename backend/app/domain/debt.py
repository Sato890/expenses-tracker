from dataclasses import dataclass

from .group import Member
from .money import Money
from .transaction import Expense


@dataclass(frozen=True)
class Debt:
    amount: Money
    debtor: Member
    creditor: Member


def calculate_debt_changes(expense: Expense) -> list[Debt]:
    debts = []

    for allocation in expense.allocations:
        if allocation.receiver == expense.payer:
            continue

        debt = Debt(allocation.share, allocation.receiver, expense.payer)
        debts.append(debt)

    return debts
