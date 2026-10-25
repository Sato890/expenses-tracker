"""Repeatable development data for the local expense workflow."""

from uuid import UUID

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from app.adapters.orm import categories, groups, members
from app.database import engine

BUILT_IN_CATEGORIES = (
    (UUID("b656752a-6d14-4882-820b-9939fa00c320"), "Dining Out"),
    (UUID("30e07b84-0535-4421-8197-0e8749413d90"), "Bars & Drinks"),
    (UUID("383d2382-a76e-40cc-9135-9b1529cddd0b"), "Travel"),
    (UUID("58a37aee-0429-4cbd-adef-ad86c144ae7b"), "Transport"),
    (UUID("59dbb424-ae7e-49a1-977d-8ed13d6bcf18"), "Health"),
    (UUID("e9fe9aec-84e6-464f-8c29-c503f576e2cd"), "Rent"),
    (UUID("3ed090a1-c2a5-4f4d-9615-e9e292744d1d"), "Utilities"),
    (UUID("9df526fc-a07e-46fc-a0ff-f0d6d502a082"), "Gaming"),
    (UUID("9a0f142f-d4db-48a3-b3c6-0bac0e37206e"), "Gifts"),
    (UUID("ff43ac28-4689-4d29-be10-55860846d8eb"), "Education"),
    (UUID("0bacd5bc-13a0-430e-a8b3-1dbf69194e8b"), "Groceries"),
    (UUID("fcca9d37-dc3d-4773-8118-109d5f6bbff3"), "Clothing"),
    (UUID("a278851f-4e1a-4dd1-9c3c-0c8b5f105198"), "Sports & Fitness"),
    (UUID("0130f1e4-9660-45eb-b9f1-0a90b3e3d9a6"), "Pets"),
    (UUID("e2a71067-87da-4167-8974-211be6502a12"), "Phone"),
)


def seed_development_data(connection: Connection) -> None:
    """Insert missing development rows without replacing existing data."""
    connection.execute(
        insert(groups)
        .values(id="group-1", name="Household")
        .on_conflict_do_nothing(constraint="pk_groups")
    )
    connection.execute(
        insert(members)
        .values(
            [
                {"group_id": "group-1", "id": "member-1", "name": "Satoshi"},
                {"group_id": "group-1", "id": "member-2", "name": "Ilaria"},
            ]
        )
        .on_conflict_do_nothing(constraint="pk_members")
    )
    connection.execute(
        insert(categories)
        .values(
            [
                {"id": category_id, "name": name}
                for category_id, name in BUILT_IN_CATEGORIES
            ]
        )
        .on_conflict_do_nothing()
    )


def main() -> None:
    """Seed the configured development database in one transaction."""
    with engine.begin() as connection:
        seed_development_data(connection)


if __name__ == "__main__":
    main()
