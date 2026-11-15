from decimal import Decimal

from .identity import Member
from .money import Money
from .transaction import Expense


def calculate_expense_balance_changes(expense: Expense) -> dict[Member, Money]:
    changes: dict[Member, Money] = {}
    zero = Money(Decimal("0"), expense.amount.currency)
    for allocation in expense.allocations:
        receiver = allocation.receiver
        if receiver is expense.payer:
            continue
        changes[expense.payer] = changes.get(expense.payer, zero) + allocation.share
        changes[receiver] = changes.get(receiver, zero) - allocation.share
    return changes
