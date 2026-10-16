"""15th migration: add private service attachments

Revision ID: c2d8e4f6a1b3
Revises: 8f4c1d2a6b7e
Create Date: 2026-09-13 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d8e4f6a1b3"
down_revision: Union[str, Sequence[str], None] = "8f4c1d2a6b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_attachments",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.CHAR(length=36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(length=36), nullable=True),
        sa.Column("service_id", sa.CHAR(length=36), nullable=False),
        sa.Column("tutor_id", sa.CHAR(length=36), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tutor_id"], ["tutors.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        "ix_service_attachments_service_id",
        "service_attachments",
        ["service_id"],
    )
    op.create_index(
        "ix_service_attachments_tutor_id",
        "service_attachments",
        ["tutor_id"],
    )


def downgrade() -> None:
    op.drop_table("service_attachments")
