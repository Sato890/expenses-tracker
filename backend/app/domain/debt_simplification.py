from heapq import heapify, heappop, heappush

from .debt import Debt
from .identity import Member
from .money import Money


def simplify_debts(settlement_amounts: dict[Member, Money]) -> list[Debt]:
    debts = []

    # Negated magnitudes put the largest amounts first in each min-heap.
    debtors = [
        (amount, member.id, member)
        for member, amount in settlement_amounts.items()
        if amount.amount < 0
    ]
    creditors = [
        (-amount, member.id, member)
        for member, amount in settlement_amounts.items()
        if amount.amount > 0
    ]
    heapify(debtors)
    heapify(creditors)

    while debtors and creditors:
        debtor_amount, _, debtor = heappop(debtors)
        creditor_amount, _, creditor = heappop(creditors)
        amount = min(-debtor_amount, -creditor_amount)
        debts.append(Debt(amount, debtor, creditor))

        debtor_remainder = debtor_amount + amount
        creditor_remainder = creditor_amount + amount
        if debtor_remainder.amount < 0:
            heappush(debtors, (debtor_remainder, debtor.id, debtor))
        if creditor_remainder.amount < 0:
            heappush(creditors, (creditor_remainder, creditor.id, creditor))

    return debts
