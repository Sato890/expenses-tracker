from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .allocation import validate_exact_allocations
from .debt import Debt, calculate_debts
from .debt_simplification import simplify_debts
from .identity import Member, User
from .money import Money
from .transaction import Expense, Settlement, Transaction


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
        if not self._has_member(expense.payer):
            raise ValueError("Payer is not in the group")

        for allocation in expense.allocations:
            if not self._has_member(allocation.receiver):
                raise ValueError("Receiver is not in the group")

        validate_exact_allocations(expense.amount, expense.allocations)

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

        self._transactions.append(settlement)

    def remove_settlement(self, settlement_id: str) -> None:
        settlement_index = self._find_settlement_index(settlement_id)
        del self._transactions[settlement_index]

    def edit_settlement(self, settlement: Settlement) -> None:
        self._validate_settlement(settlement)
        settlement_index = self._find_settlement_index(settlement.settlement_id)
        self._transactions[settlement_index] = settlement

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
