"""add_withdrawn_to_ticketstatus_enum

Revision ID: b4d1e7f23a09
Revises: 54409ce92d72
Create Date: 2026-08-21 13:10:00.000000

Purpose:
    Adds the WITHDRAWN value to the PostgreSQL ticketstatus enum type.

    This value exists in the application's TicketStatus enum
    (app/core/constants.py) and is actively used by ticket withdrawal
    features in ticket_routes.py and ticket_service.py, but was never
    included in any previous Alembic migration.

    It is also required for historical ticket_status_history rows where
    old_status='WITHDRAWN' (2 rows in SQLite data: ids 56 and 69).

Technical note:
    ALTER TYPE ... ADD VALUE cannot run inside a PostgreSQL transaction.
    We use Alembic's op.get_context().autocommit_block() (available in
    Alembic >= 1.12, confirmed: project uses 1.18.2) to temporarily step
    outside the wrapping transaction for this single DDL statement.

    IF NOT EXISTS prevents the migration from failing if the value is
    somehow already present.

Downgrade:
    PostgreSQL does not support removing enum values without dropping and
    recreating the type. Downgrade is intentionally a no-op to avoid
    destructive schema changes.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4d1e7f23a09'
down_revision = '54409ce92d72'
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PostgreSQL.
    # autocommit_block() temporarily steps outside the transaction for this
    # single DDL statement only. Alembic then opens a new transaction to
    # stamp the alembic_version table.
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "ALTER TYPE ticketstatus ADD VALUE IF NOT EXISTS 'WITHDRAWN'"
        ))


def downgrade():
    # PostgreSQL does not support ALTER TYPE ... DROP VALUE.
    # Removing an enum value requires DROP TYPE + CREATE TYPE + ALTER all
    # columns using it -- a destructive, high-risk operation.
    # This downgrade is intentionally a no-op.
    pass
