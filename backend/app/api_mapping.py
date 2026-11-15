from app.api_responses import AllocationResponse, ExpenseResponse
from app.domain.money import Money
from app.domain.transaction import Expense


def build_expense_response(group_id: str, expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.expense_id,
        group_id=group_id,
        type="expense",
        amount=str(expense.amount.amount),
        currency=expense.amount.currency,
        payer_id=expense.payer.id,
        date=expense.date,
        category_id=expense.category.id,
        allocations=[
            AllocationResponse(
                receiver_id=allocation.receiver.id,
                amount=str(allocation.share.amount),
            )
            for allocation in expense.allocations
        ],
    )


def format_settlement_amount(amount: Money) -> str:
    if amount.amount == 0:
        return "0"
    return format(amount.amount, "f")
