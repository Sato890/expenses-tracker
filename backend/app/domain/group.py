from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Context, Decimal, localcontext
from typing import TYPE_CHECKING

from .money import CALCULATION_PRECISION

if TYPE_CHECKING:
    from .debt import Debt
    from .transaction import Expense, Transaction


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
    _transactions: list[Transaction] = field(
        default_factory=list, init=False, repr=False
    )

    @property
    def transactions(self) -> tuple[Transaction, ...]:
        return tuple(self._transactions)

    @property
    def debts(self) -> list[Debt]:
        from .debt import calculate_debts
        from .transaction import Expense

        expenses = [
            transaction
            for transaction in self._transactions
            if isinstance(transaction, Expense)
        ]
        return calculate_debts(expenses)

    def calculate_member_settlement_amounts(self) -> dict[Member, Decimal]:
        settlement_amounts = {member: Decimal("0") for member in self.members}

        with localcontext(Context(prec=CALCULATION_PRECISION)):
            for debt in self.debts:
                settlement_amounts[debt.debtor] -= debt.amount.amount
                settlement_amounts[debt.creditor] += debt.amount.amount

        return settlement_amounts

    def add_expense(self, expense: Expense) -> None:
        from .transaction import Expense

        self._validate_expense(expense)

        if any(
            isinstance(transaction, Expense)
            and transaction.expense_id == expense.expense_id
            for transaction in self._transactions
        ):
            raise ValueError("Expense ID already exists in the group")

        self._transactions.append(expense)

    def remove_expense(self, expense_id: str) -> None:
        expense_index = self._find_expense_index(expense_id)
        del self._transactions[expense_index]

    def edit_expense(self, expense: Expense) -> None:
        self._validate_expense(expense)
        expense_index = self._find_expense_index(expense.expense_id)
        self._transactions[expense_index] = expense

    def _validate_expense(self, expense: Expense) -> None:
        from .allocation import validate_exact_allocations

        if expense.payer not in self.members:
            raise ValueError("Payer is not in the group")

        for allocation in expense.allocations:
            if allocation.receiver not in self.members:
                raise ValueError("Receiver is not in the group")

        validate_exact_allocations(expense.amount, list(expense.allocations))

    def _find_expense_index(self, expense_id: str) -> int:
        from .transaction import Expense

        for index, transaction in enumerate(self._transactions):
            if (
                isinstance(transaction, Expense)
                and transaction.expense_id == expense_id
            ):
                return index

        raise ValueError("Expense is not in the group")
