"""Add per-group revisions and changed entity IDs.

Revision ID: 4e7c00000001
Revises: 6b7c8d9e0f12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4e7c00000001"
down_revision: str | Sequence[str] | None = "6b7c8d9e0f12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column("revision", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.create_table(
        "group_changes",
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint(
            "group_id", "revision", "entity_type", "entity_id", name="pk_group_changes"
        ),
    )


def downgrade() -> None:
    op.drop_table("group_changes")
    op.drop_column("groups", "revision")
