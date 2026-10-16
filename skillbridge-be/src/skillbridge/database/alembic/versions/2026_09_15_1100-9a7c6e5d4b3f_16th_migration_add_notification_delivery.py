"""16th migration: track notification delivery separately from read state.

Revision ID: 9a7c6e5d4b3f
Revises: c2d8e4f6a1b3
Create Date: 2026-09-15 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7c6e5d4b3f"
down_revision: Union[str, Sequence[str], None] = "c2d8e4f6a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "is_delivered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        sa.text("UPDATE notifications SET is_delivered = 1")
    )
    op.create_index(
        "ix_notifications_user_delivered",
        "notifications",
        ["user_id", "is_delivered"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_delivered", table_name="notifications")
    op.drop_column("notifications", "is_delivered")