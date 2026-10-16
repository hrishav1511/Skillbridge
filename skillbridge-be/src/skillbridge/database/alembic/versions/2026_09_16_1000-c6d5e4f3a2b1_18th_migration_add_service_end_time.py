"""18th migration: add service end times.

Revision ID: c6d5e4f3a2b1
Revises: b4e8d7c6a5f4
Create Date: 2026-09-16 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6d5e4f3a2b1"
down_revision: Union[str, Sequence[str], None] = "b4e8d7c6a5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column("end_time", sa.Time(), nullable=True),
    )
    op.add_column(
        "service_revisions",
        sa.Column("end_time", sa.Time(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_revisions", "end_time")
    op.drop_column("services", "end_time")