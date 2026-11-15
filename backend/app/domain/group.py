from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from .allocation import validate_exact_allocations
from .debt import Debt, calculate_debts
from .debt_simplification import simplify_debts
from .identity import Member, User
from .money import Money
from .settlement_amounts import calculate_expense_balance_changes
from .transaction import Expense, Settlement, Transaction


def validate_expense_for_members(expense: Expense, members: Sequence[Member]) -> None:
    if not any(member is expense.payer for member in members):
        raise ValueError("Payer is not in the group")

    for allocation in expense.allocations:
        if not any(member is allocation.receiver for member in members):
            raise ValueError("Receiver is not in the group")

    validate_exact_allocations(expense.amount, expense.allocations)


@dataclass
class Group:
    id: str
    name: str
    _members: list[Member] = field(default_factory=list)
    member_to_user: dict[Member, User] = field(default_factory=dict)
    _transactions: list[Transaction] = field(
        default_factory=list, init=False, repr=False
    )

    def __post_init__(self) -> None:
        members = self._members
        self._members = []
        for member in members:
            self.add_member(member)

    @property
    def members(self) -> tuple[Member, ...]:
        return tuple(self._members)

    @property
    def transactions(self) -> tuple[Transaction, ...]:
        return tuple(self._transactions)

    @property
    def debts(self) -> list[Debt]:
        return calculate_debts(self._transactions)

    def add_member(self, new_member: Member) -> None:
        if any(member.id == new_member.id for member in self._members):
            raise ValueError("Member ID already exists in the group")
        self._members.append(new_member)

    def remove_member(self, remove_member_id: str) -> None:
        member_index = next(
            (
                index
                for index, member in enumerate(self._members)
                if member.id == remove_member_id
            ),
            None,
        )
        if member_index is None:
            raise ValueError("Member is not in the group")

        for transaction in self._transactions:
            if transaction.payer.id == remove_member_id:
                raise ValueError("Member has associated transactions")
            if isinstance(transaction, Settlement):
                if transaction.receiver.id == remove_member_id:
                    raise ValueError("Member has associated transactions")
            elif isinstance(transaction, Expense) and any(
                allocation.receiver.id == remove_member_id
                for allocation in transaction.allocations
            ):
                raise ValueError("Member has associated transactions")

        removed_member = self._members.pop(member_index)
        self.member_to_user.pop(removed_member, None)

    def calculate_member_settlement_amounts(self) -> dict[Member, Money]:
        settlement_amounts = {
            member: Money(Decimal("0"), "EUR") for member in self.members
        }

        for debt in self.debts:
            settlement_amounts[debt.debtor] -= debt.amount
            settlement_amounts[debt.creditor] += debt.amount

        return settlement_amounts

    def simplify_debts(self) -> list[Debt]:
        return simplify_debts(self.calculate_member_settlement_amounts())

    def add_expense(self, expense: Expense) -> None:
        validate_expense_for_members(expense, self._members)

        if any(
            isinstance(transaction, Expense)
            and transaction.expense_id == expense.expense_id
            for transaction in self._transactions
        ):
            raise ValueError("Expense ID already exists in the group")

        self._apply_expense_change(expense)
        self._transactions.append(expense)

    def remove_expense(self, expense_id: str) -> None:
        expense_index = self._find_expense_index(expense_id)
        original = self._transactions[expense_index]
        self._apply_expense_change(original, reverse=True)
        del self._transactions[expense_index]

    def edit_expense(self, expense: Expense) -> None:
        validate_expense_for_members(expense, self._members)
        expense_index = self._find_expense_index(expense.expense_id)
        original = self._transactions[expense_index]
        self._apply_expense_change(original, reverse=True)
        self._apply_expense_change(expense)
        self._transactions[expense_index] = expense

    def _apply_expense_change(self, expense: Expense, reverse: bool = False) -> None:
        for member, change in calculate_expense_balance_changes(expense).items():
            member.adjust_settlement_balance(-change if reverse else change)

    def _find_expense_index(self, expense_id: str) -> int:
        for index, transaction in enumerate(self._transactions):
            if (
                isinstance(transaction, Expense)
                and transaction.expense_id == expense_id
            ):
                return index

        raise ValueError("Expense is not in the group")

    def add_settlement(self, settlement: Settlement) -> None:
        self._validate_settlement(settlement)

        if any(
            isinstance(transaction, Settlement)
            and transaction.settlement_id == settlement.settlement_id
            for transaction in self._transactions
        ):
            raise ValueError("Settlement ID already exists in the group")

        self._apply_settlement_change(settlement)
        self._transactions.append(settlement)

    def remove_settlement(self, settlement_id: str) -> None:
        settlement_index = self._find_settlement_index(settlement_id)
        original = self._transactions[settlement_index]
        self._apply_settlement_change(original, reverse=True)
        del self._transactions[settlement_index]

    def edit_settlement(self, settlement: Settlement) -> None:
        self._validate_settlement(settlement)
        settlement_index = self._find_settlement_index(settlement.settlement_id)
        original = self._transactions[settlement_index]
        self._apply_settlement_change(original, reverse=True)
        self._apply_settlement_change(settlement)
        self._transactions[settlement_index] = settlement

    def _apply_settlement_change(
        self, settlement: Settlement, reverse: bool = False
    ) -> None:
        if settlement.payer is settlement.receiver:
            return
        payer_change = -settlement.amount if reverse else settlement.amount
        settlement.payer.adjust_settlement_balance(payer_change)
        settlement.receiver.adjust_settlement_balance(-payer_change)

    def _validate_settlement(self, settlement: Settlement) -> None:
        if not self._has_member(settlement.payer):
            raise ValueError("Payer is not in the group")
        if not self._has_member(settlement.receiver):
            raise ValueError("Receiver is not in the group")
        if settlement.amount.amount <= 0:
            raise ValueError("Settlement amount must be positive")

    def _has_member(self, candidate: Member) -> bool:
        return any(member is candidate for member in self._members)

    def _find_settlement_index(self, settlement_id: str) -> int:
        for index, transaction in enumerate(self._transactions):
            if (
                isinstance(transaction, Settlement)
                and transaction.settlement_id == settlement_id
            ):
                return index

        raise ValueError("Settlement is not in the group")
