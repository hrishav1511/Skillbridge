"""Add report tables and security uniqueness constraints.

Revision ID: 7ac91e2d4f60
Revises: 21f90e7b8d11
Create Date: 2026-09-19 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "7ac91e2d4f60"
down_revision: Union[str, Sequence[str], None] = "21f90e7b8d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_offline_mode() -> bool:
    try:
        return context.is_offline_mode()
    except NameError:
        return False


def _inspector():
    """Return a fresh inspector so DDL executed earlier is visible on MySQL."""
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if _is_offline_mode():
        return False
    return _inspector().has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    if _is_offline_mode():
        return False
    return any(
        index["name"] == index_name for index in _inspector().get_indexes(table_name)
    )


def _has_unique_columns(table_name: str, column_names: Sequence[str]) -> bool:
    """Check unique constraints and indexes, including create_all variants."""
    if _is_offline_mode():
        return False
    expected = tuple(column_names)
    inspector = _inspector()
    unique_constraints = inspector.get_unique_constraints(table_name)
    indexes = inspector.get_indexes(table_name)
    return any(
        tuple(constraint.get("column_names") or ()) == expected
        for constraint in unique_constraints
    ) or any(
        index.get("unique") and tuple(index.get("column_names") or ()) == expected
        for index in indexes
    )


def _column_is_nullable(table_name: str, column_name: str) -> bool:
    if _is_offline_mode():
        return True
    return next(
        column["nullable"]
        for column in _inspector().get_columns(table_name)
        if column["name"] == column_name
    )


def _base_columns():
    return [
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
    ]


def upgrade() -> None:
    # Some legacy/bootstrap flows use Base.metadata.create_all(). Also, MySQL
    # DDL is non-transactional, so a failed attempt can leave earlier objects
    # behind. Make this revision safe to run in either situation.
    if not _has_table("reported_tutors"):
        op.create_table(
            "reported_tutors",
            *_base_columns(),
            sa.Column("student_id", sa.CHAR(length=36), nullable=False),
            sa.Column("tutor_id", sa.CHAR(length=36), nullable=False),
            sa.Column("reason", sa.String(length=1024), nullable=False),
            sa.Column(
                "reported_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["student_id"], ["students.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["tutor_id"], ["tutors.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["created_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["updated_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_table("reported_services"):
        op.create_table(
            "reported_services",
            *_base_columns(),
            sa.Column("student_id", sa.CHAR(length=36), nullable=False),
            sa.Column("service_id", sa.CHAR(length=36), nullable=False),
            sa.Column("reason", sa.String(length=1024), nullable=False),
            sa.Column(
                "reported_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["student_id"], ["students.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["service_id"], ["services.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["created_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["updated_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if _column_is_nullable("users", "email"):
        op.alter_column(
            "users", "email", existing_type=sa.String(length=255), nullable=False
        )
    if not _has_index("users", "ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.alter_column(
        "users", "email", existing_type=sa.String(length=255), nullable=True
    )
    op.drop_table("reported_services")
    op.drop_table("reported_tutors")
