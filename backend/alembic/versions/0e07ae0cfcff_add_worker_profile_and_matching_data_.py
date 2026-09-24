"""add worker profile and matching data fields

Revision ID: 0e07ae0cfcff
Revises: 45f5b1be1f76
Create Date: 2026-09-24 04:39:28.237435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e07ae0cfcff'
down_revision: Union[str, Sequence[str], None] = '45f5b1be1f76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Same deterministic placeholder values as app/models/worker.py's
# DEFAULT_WORKER_* constants, used only to backfill any Worker rows that
# already exist in the database before this migration runs (Phase 5C/5E
# never created any worker-creation endpoint, so a fresh database has
# none, but this migration is written to be safe on one that does).
_DEFAULT_ADDRESS = "Not Provided"
_DEFAULT_PINCODE = "000000"
_DEFAULT_RATING = "0.00"
_DEFAULT_TOTAL_JOBS_COMPLETED = "0"


def upgrade() -> None:
    """
    Upgrade schema.

    Safe on a `workers` table that already has rows: every new column is
    added NULLABLE first (an instant metadata-only change, no table
    rewrite, no risk of failing on existing rows), existing rows are then
    explicitly backfilled with a deterministic placeholder value, and
    only then are the columns tightened to NOT NULL and the CHECK
    constraints added -- by which point every row, old or new, already
    satisfies them.
    """
    # Step 1: add the four new columns as nullable.
    op.add_column("workers", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("workers", sa.Column("pincode", sa.String(length=6), nullable=True))
    op.add_column("workers", sa.Column("rating", sa.Numeric(3, 2), nullable=True))
    op.add_column(
        "workers", sa.Column("total_jobs_completed", sa.Integer(), nullable=True)
    )

    # Step 2: backfill any existing rows with the deterministic
    # placeholder values (a no-op on a table with no rows).
    op.execute(f"UPDATE workers SET address = '{_DEFAULT_ADDRESS}' WHERE address IS NULL")
    op.execute(f"UPDATE workers SET pincode = '{_DEFAULT_PINCODE}' WHERE pincode IS NULL")
    op.execute(f"UPDATE workers SET rating = {_DEFAULT_RATING} WHERE rating IS NULL")
    op.execute(
        "UPDATE workers SET total_jobs_completed = "
        f"{_DEFAULT_TOTAL_JOBS_COMPLETED} WHERE total_jobs_completed IS NULL"
    )

    # Step 3: every row now has a value -- safe to require one.
    op.alter_column("workers", "address", nullable=False)
    op.alter_column("workers", "pincode", nullable=False)
    op.alter_column("workers", "rating", nullable=False)
    op.alter_column("workers", "total_jobs_completed", nullable=False)

    # Step 4: add the CHECK constraints. These run after the backfill, so
    # they validate against already-consistent data rather than racing
    # the UPDATEs above.
    op.create_check_constraint(
        "ck_workers_pincode_six_digits", "workers", "pincode ~ '^[0-9]{6}$'"
    )
    op.create_check_constraint(
        "ck_workers_rating_range", "workers", "rating >= 0 AND rating <= 5"
    )
    op.create_check_constraint(
        "ck_workers_total_jobs_completed_non_negative",
        "workers",
        "total_jobs_completed >= 0",
    )


def downgrade() -> None:
    """Downgrade schema. Reverses upgrade() exactly, dropping constraints before columns."""
    op.drop_constraint("ck_workers_total_jobs_completed_non_negative", "workers", type_="check")
    op.drop_constraint("ck_workers_rating_range", "workers", type_="check")
    op.drop_constraint("ck_workers_pincode_six_digits", "workers", type_="check")

    op.drop_column("workers", "total_jobs_completed")
    op.drop_column("workers", "rating")
    op.drop_column("workers", "pincode")
    op.drop_column("workers", "address")
