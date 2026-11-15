from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, text

from app.adapters.orm import metadata


def test_migration_backfills_exact_member_amounts_from_existing_expenses(
    schema_engine: Engine,
) -> None:
    with schema_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO groups (id, name) VALUES ('household', 'Household')")
        )
        connection.execute(
            text("""
                INSERT INTO members (group_id, id, name)
                VALUES ('household', 'alex', 'Alex'),
                       ('household', 'bea', 'Bea'),
                       ('household', 'cam', 'Cam')
            """)
        )
        connection.execute(
            text("""
                INSERT INTO categories (id, name)
                VALUES ('00000000-0000-0000-0000-000000000001', 'Groceries')
            """)
        )
        connection.execute(
            text("""
                INSERT INTO expenses
                    (group_id, id, amount, currency, payer_id, date, category_id)
                VALUES ('household', 'old', 10.005, 'EUR', 'alex',
                        DATE '2026-11-01', '00000000-0000-0000-0000-000000000001')
            """)
        )
        connection.execute(
            text("""
                INSERT INTO allocations
                    (group_id, expense_id, receiver_id, amount, currency)
                VALUES ('household', 'old', 'alex', 3.335, 'EUR'),
                       ('household', 'old', 'bea', 3.335, 'EUR'),
                       ('household', 'old', 'cam', 3.335, 'EUR')
            """)
        )
        connection.execute(text("ALTER TABLE members DROP COLUMN settlement_balance"))

    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "6b7c8d9e0f12_store_member_settlement_balances.py"
    )
    spec = spec_from_file_location("member_balance_migration", path)
    assert spec is not None
    assert spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    with schema_engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        amounts = connection.execute(
            text("""
                SELECT id, settlement_balance FROM members
                WHERE group_id = 'household' ORDER BY id
            """)
        ).all()
        assert compare_metadata(MigrationContext.configure(connection), metadata) == []

    assert amounts == [
        ("alex", Decimal("6.670")),
        ("bea", Decimal("-3.335")),
        ("cam", Decimal("-3.335")),
    ]
