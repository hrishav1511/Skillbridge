"""19th migration: add student tutor and service favorites.

Revision ID: d7e6f5a4b3c2
Revises: c6d5e4f3a2b1
Create Date: 2026-09-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e6f5a4b3c2"
down_revision: Union[str, Sequence[str], None] = "c6d5e4f3a2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns():
    return [
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.CHAR(length=36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(length=36), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "student_favorite_tutors",
        *_base_columns(),
        sa.Column("student_id", sa.CHAR(length=36), nullable=False),
        sa.Column("tutor_id", sa.CHAR(length=36), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tutor_id"], ["tutors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "tutor_id", name="uq_student_favorite_tutor"),
    )
    op.create_table(
        "student_favorite_services",
        *_base_columns(),
        sa.Column("student_id", sa.CHAR(length=36), nullable=False),
        sa.Column("service_id", sa.CHAR(length=36), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "service_id", name="uq_student_favorite_service"),
    )


def downgrade() -> None:
    op.drop_table("student_favorite_services")
    op.drop_table("student_favorite_tutors")