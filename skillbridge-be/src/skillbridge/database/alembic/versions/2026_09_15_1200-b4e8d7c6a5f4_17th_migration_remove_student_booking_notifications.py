"""17th migration: remove booking notifications from student accounts.

Revision ID: b4e8d7c6a5f4
Revises: 9a7c6e5d4b3f
Create Date: 2026-09-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e8d7c6a5f4"
down_revision: Union[str, Sequence[str], None] = "9a7c6e5d4b3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM notifications
            WHERE notification_type = 'SERVICE_BOOKED'
              AND user_id IN (
                  SELECT user_id
                  FROM user_role_associations
                  WHERE student_id IS NOT NULL
              )
            """
        )
    )


def downgrade() -> None:
    pass