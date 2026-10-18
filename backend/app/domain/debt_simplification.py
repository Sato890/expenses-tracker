from decimal import Context, Decimal, localcontext
from heapq import heapify, heappop, heappush

from .debt import Debt
from .identity import Member
from .money import CALCULATION_PRECISION, Money


def simplify_debts(settlement_amounts: dict[Member, Decimal]) -> list[Debt]:
    debts = []

    with localcontext(Context(prec=CALCULATION_PRECISION)):
        # Negated magnitudes put the largest amounts first in each min-heap.
        debtors = [
            (amount, member.id, member)
            for member, amount in settlement_amounts.items()
            if amount < 0
        ]
        creditors = [
            (-amount, member.id, member)
            for member, amount in settlement_amounts.items()
            if amount > 0
        ]
        heapify(debtors)
        heapify(creditors)

        while debtors and creditors:
            debtor_amount, _, debtor = heappop(debtors)
            creditor_amount, _, creditor = heappop(creditors)
            amount = min(-debtor_amount, -creditor_amount)
            debts.append(Debt(Money(amount, "EUR"), debtor, creditor))

            debtor_remainder = debtor_amount + amount
            creditor_remainder = creditor_amount + amount
            if debtor_remainder < 0:
                heappush(debtors, (debtor_remainder, debtor.id, debtor))
            if creditor_remainder < 0:
                heappush(creditors, (creditor_remainder, creditor.id, creditor))

    return debts
