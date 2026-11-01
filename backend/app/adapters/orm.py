"""SQLAlchemy mappings kept outside the domain model."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    and_,
    event,
    inspect,
)
from sqlalchemy.orm import composite, foreign, registry, relationship

from app.domain.allocation import Allocation
from app.domain.group import Group
from app.domain.identity import Member
from app.domain.money import Money
from app.domain.transaction import Category, Expense

mapper_registry = registry()
metadata = mapper_registry.metadata

groups = Table(
    "groups",
    metadata,
    Column("id", String, nullable=False),
    Column("name", String, nullable=False),
    PrimaryKeyConstraint("id", name="pk_groups"),
)

members = Table(
    "members",
    metadata,
    Column(
        "group_id",
        String,
        ForeignKey("groups.id", name="fk_members_group_id_groups"),
        nullable=False,
    ),
    Column("id", String, nullable=False),
    Column("name", String, nullable=False),
    PrimaryKeyConstraint("group_id", "id", name="pk_members"),
)

categories = Table(
    "categories",
    metadata,
    Column("id", Uuid, nullable=False),
    Column("name", String, nullable=False),
    PrimaryKeyConstraint("id", name="pk_categories"),
    UniqueConstraint("name", name="uq_categories_name"),
)

expenses = Table(
    "expenses",
    metadata,
    Column(
        "group_id",
        String,
        ForeignKey("groups.id", name="fk_expenses_group_id_groups"),
        nullable=False,
    ),
    Column("id", String, nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("currency", String, nullable=False),
    Column("payer_id", String, nullable=False),
    Column("date", Date, nullable=False),
    Column(
        "category_id",
        Uuid,
        ForeignKey("categories.id", name="fk_expenses_category_id_categories"),
        nullable=False,
    ),
    PrimaryKeyConstraint("group_id", "id", name="pk_expenses"),
    ForeignKeyConstraint(
        ["group_id", "payer_id"],
        ["members.group_id", "members.id"],
        name="fk_expenses_payer_members",
    ),
    CheckConstraint(
        "amount > 0 AND amount < 1e18",
        name="ck_expenses_amount_bounds",
    ),
    CheckConstraint("amount = trunc(amount, 18)", name="ck_expenses_amount_precision"),
)

allocations = Table(
    "allocations",
    metadata,
    Column("group_id", String, nullable=False),
    Column("expense_id", String, nullable=False),
    Column("receiver_id", String, nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("currency", String, nullable=False),
    PrimaryKeyConstraint(
        "group_id", "expense_id", "receiver_id", name="pk_allocations"
    ),
    ForeignKeyConstraint(
        ["group_id", "expense_id"],
        ["expenses.group_id", "expenses.id"],
        name="fk_allocations_expense_expenses",
    ),
    ForeignKeyConstraint(
        ["group_id", "receiver_id"],
        ["members.group_id", "members.id"],
        name="fk_allocations_receiver_members",
    ),
    CheckConstraint(
        "amount > 0 AND amount < 1e18",
        name="ck_allocations_amount_bounds",
    ),
    CheckConstraint(
        "amount = trunc(amount, 18)", name="ck_allocations_amount_precision"
    ),
)


def _initialize_unmapped_group_state(group: Group, _context: object) -> None:
    group.member_to_user = {}


def start_mappers() -> None:
    """Map domain classes at the application or test boundary."""
    if inspect(Group, raiseerr=False) is not None:
        return

    mapper_registry.map_imperatively(
        Member,
        members,
        properties={
            "_id": members.c.id,
            "_name": members.c.name,
            "_group_id": members.c.group_id,
        },
    )
    mapper_registry.map_imperatively(
        Category,
        categories,
        properties={"_id": categories.c.id, "_name": categories.c.name},
    )
    mapper_registry.map_imperatively(
        Allocation,
        allocations,
        properties={
            "_group_id": allocations.c.group_id,
            "_expense_id": allocations.c.expense_id,
            "_receiver_id": allocations.c.receiver_id,
            "_share_value": allocations.c.amount,
            "_currency": allocations.c.currency,
            "_share": composite(Money, "_share_value", "_currency"),
            "_receiver": relationship(
                Member,
                primaryjoin=and_(
                    allocations.c.group_id == members.c.group_id,
                    foreign(allocations.c.receiver_id) == members.c.id,
                ),
                lazy="selectin",
            ),
        },
    )
    mapper_registry.map_imperatively(
        Expense,
        expenses,
        properties={
            "_expense_id": expenses.c.id,
            "_group_id": expenses.c.group_id,
            "_amount_value": expenses.c.amount,
            "_currency": expenses.c.currency,
            "_amount": composite(Money, "_amount_value", "_currency"),
            "_date": expenses.c.date,
            "_payer_id": expenses.c.payer_id,
            "_category_id": expenses.c.category_id,
            "_payer": relationship(
                Member,
                primaryjoin=and_(
                    expenses.c.group_id == members.c.group_id,
                    foreign(expenses.c.payer_id) == members.c.id,
                ),
                lazy="selectin",
            ),
            "_category": relationship(Category, lazy="selectin"),
            "_allocations": relationship(
                Allocation,
                order_by=allocations.c.receiver_id,
                lazy="selectin",
                cascade="all, delete-orphan",
            ),
        },
    )
    mapper_registry.map_imperatively(
        Group,
        groups,
        properties={
            "_members": relationship(
                Member,
                order_by=members.c.id,
                lazy="selectin",
                cascade="all, delete-orphan",
            ),
            "_transactions": relationship(
                Expense,
                order_by=(expenses.c.date.desc(), expenses.c.id.desc()),
                lazy="selectin",
                cascade="all, delete-orphan",
            ),
        },
    )
    event.listen(Group, "load", _initialize_unmapped_group_state)
