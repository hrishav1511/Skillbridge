"""Widen tutor free-text columns so long bios stop failing the update.

`bio` and `teaching_style` were VARCHAR(255) while the Edit Profile form places
no upper bound on them. SQLite silently truncates nothing and accepts the row,
but MySQL in strict mode raises "Data too long for column", which surfaces to
the browser as an opaque 500 on PUT /api/v1/tutor/{tutor_id}/. TEXT removes the
ceiling; the application still bounds the input so oversized payloads come back
as a named validation error rather than a database failure.

Revision ID: c03f5b7e8d90
Revises: b92e4a6d7c8f
Create Date: 2026-09-19 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c03f5b7e8d90"
down_revision: Union[str, Sequence[str], None] = "b92e4a6d7c8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) pairs that hold free-form tutor prose.
_COLUMNS: Sequence[tuple[str, str]] = (
    ("tutors", "bio"),
    ("tutors", "teaching_style"),
    ("tutor_revisions", "bio"),
    ("tutor_revisions", "teaching_style"),
)


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    for table_name, column_name in _COLUMNS:
        if column_name not in _existing_columns(table_name):
            continue
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Rows longer than 255 characters cannot survive the narrowing, so trim them
    # first rather than letting the ALTER fail half way through.
    for table_name, column_name in _COLUMNS:
        if column_name not in _existing_columns(table_name):
            continue
        op.execute(
            sa.text(
                f"UPDATE {table_name} SET {column_name} = LEFT({column_name}, 255) "
                f"WHERE {column_name} IS NOT NULL AND LENGTH({column_name}) > 255"
            )
        )
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
