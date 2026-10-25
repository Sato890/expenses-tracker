"""SQLAlchemy mappings kept outside the domain model."""

from sqlalchemy import (
    Column,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import registry, relationship

from app.domain.group import Group
from app.domain.identity import Member
from app.domain.transaction import Category

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


def _initialize_unmapped_group_state(group: Group, _context: object) -> None:
    group.member_to_user = {}
    group._transactions = []


def start_mappers() -> None:
    """Map domain classes at the application or test boundary."""
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
        Group,
        groups,
        properties={
            "_members": relationship(
                Member,
                order_by=members.c.id,
                lazy="selectin",
                cascade="all, delete-orphan",
            )
        },
    )
    event.listen(Group, "load", _initialize_unmapped_group_state)
