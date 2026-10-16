"""22nd migration: add profile picture URL for students

Revision ID: 21f90e7b8d11
Revises: 34a452565bdf
Create Date: 2026-09-18 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "21f90e7b8d11"
down_revision: Union[str, Sequence[str], None] = "34a452565bdf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("profile_picture_url", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("students", "profile_picture_url")
