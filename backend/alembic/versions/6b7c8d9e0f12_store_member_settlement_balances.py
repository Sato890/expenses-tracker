"""store member settlement balances

Revision ID: 6b7c8d9e0f12
Revises: 9585d0a70fb9

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6b7c8d9e0f12"
down_revision: str | Sequence[str] | None = "9585d0a70fb9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column(
            "settlement_balance", sa.Numeric(), nullable=False, server_default="0"
        ),
    )
    op.create_check_constraint(
        "ck_members_settlement_balance_precision",
        "members",
        "settlement_balance = trunc(settlement_balance, 18)",
    )
    op.execute("""
        WITH contributions AS (
            SELECT e.group_id, e.payer_id AS member_id, SUM(a.amount) AS amount
            FROM expenses e
            JOIN allocations a
              ON a.group_id = e.group_id AND a.expense_id = e.id
            WHERE a.receiver_id <> e.payer_id
            GROUP BY e.group_id, e.payer_id
            UNION ALL
            SELECT a.group_id, a.receiver_id AS member_id, -SUM(a.amount) AS amount
            FROM expenses e
            JOIN allocations a
              ON a.group_id = e.group_id AND a.expense_id = e.id
            WHERE a.receiver_id <> e.payer_id
            GROUP BY a.group_id, a.receiver_id
        ), totals AS (
            SELECT group_id, member_id, SUM(amount) AS settlement_balance
            FROM contributions
            GROUP BY group_id, member_id
        )
        UPDATE members AS m
        SET settlement_balance = totals.settlement_balance
        FROM totals
        WHERE m.group_id = totals.group_id AND m.id = totals.member_id
    """)


def downgrade() -> None:
    op.drop_constraint(
        "ck_members_settlement_balance_precision", "members", type_="check"
    )
    op.drop_column("members", "settlement_balance")
