"""Deduplicate legacy rows before enforcing security uniqueness keys.

Revision ID: b92e4a6d7c8f
Revises: a81d2f3c4b5e
Create Date: 2026-09-19 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "b92e4a6d7c8f"
down_revision: Union[str, Sequence[str], None] = "a81d2f3c4b5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_offline_mode() -> bool:
    try:
        return context.is_offline_mode()
    except NameError:
        return False


def _inspector():
    return sa.inspect(op.get_bind())


def _has_unique_columns(table_name: str, column_names: Sequence[str]) -> bool:
    if _is_offline_mode():
        return False
    expected = tuple(column_names)
    inspector = _inspector()
    return any(
        tuple(constraint.get("column_names") or ()) == expected
        for constraint in inspector.get_unique_constraints(table_name)
    ) or any(
        index.get("unique") and tuple(index.get("column_names") or ()) == expected
        for index in inspector.get_indexes(table_name)
    )


def _has_unique_name(table_name: str, constraint_name: str) -> bool:
    if _is_offline_mode():
        return True
    return any(
        constraint.get("name") == constraint_name
        for constraint in _inspector().get_unique_constraints(table_name)
    )


def _deduplicate_rows(
    table_name: str,
    key_columns: Sequence[str],
    temporary_table: str,
    reported_review_column: str | None = None,
) -> None:
    partition = ", ".join(key_columns)
    op.execute(f"DROP TEMPORARY TABLE IF EXISTS {temporary_table}")
    op.execute(f"""
        CREATE TEMPORARY TABLE {temporary_table} AS
        SELECT duplicate_id, keeper_id
        FROM (
            SELECT
                id AS duplicate_id,
                FIRST_VALUE(id) OVER (
                    PARTITION BY {partition}
                    ORDER BY (deleted_at IS NOT NULL), (created_at IS NULL),
                             created_at DESC, id DESC
                ) AS keeper_id,
                ROW_NUMBER() OVER (
                    PARTITION BY {partition}
                    ORDER BY (deleted_at IS NOT NULL), (created_at IS NULL),
                             created_at DESC, id DESC
                ) AS duplicate_number
            FROM {table_name}
        ) AS ranked
        WHERE duplicate_number > 1
        """)

    if reported_review_column is not None:
        # Preserve one report per reporter/kept review. UPDATE IGNORE leaves
        # conflicting reports on the duplicate, and the following DELETE
        # removes only those redundant reports before the review is removed.
        op.execute(f"""
            UPDATE IGNORE reported_reviews AS report
            INNER JOIN {temporary_table} AS duplicate
                ON report.{reported_review_column} = duplicate.duplicate_id
            SET report.{reported_review_column} = duplicate.keeper_id
            """)
        op.execute(f"""
            DELETE report
            FROM reported_reviews AS report
            INNER JOIN {temporary_table} AS duplicate
                ON report.{reported_review_column} = duplicate.duplicate_id
            """)

    op.execute(f"""
        DELETE duplicate_row
        FROM {table_name} AS duplicate_row
        INNER JOIN {temporary_table} AS duplicate
            ON duplicate_row.id = duplicate.duplicate_id
        """)
    op.execute(f"DROP TEMPORARY TABLE {temporary_table}")


def upgrade() -> None:
    if not _has_unique_columns("users", ["email"]):
        op.create_unique_constraint("uq_users_email", "users", ["email"])

    if not _has_unique_columns("user_role_associations", ["user_id", "role_id"]):
        _deduplicate_rows(
            "user_role_associations",
            ["user_id", "role_id"],
            "tmp_duplicate_user_roles",
        )
        op.create_unique_constraint(
            "uq_user_role_association",
            "user_role_associations",
            ["user_id", "role_id"],
        )

    if not _has_unique_columns("tutor_reviews", ["tutor_id", "student_id"]):
        _deduplicate_rows(
            "tutor_reviews",
            ["tutor_id", "student_id"],
            "tmp_duplicate_tutor_reviews",
            "tutor_review_id",
        )
        op.create_unique_constraint(
            "uq_tutor_review_tutor_student",
            "tutor_reviews",
            ["tutor_id", "student_id"],
        )

    if not _has_unique_columns("service_reviews", ["service_id", "student_id"]):
        _deduplicate_rows(
            "service_reviews",
            ["service_id", "student_id"],
            "tmp_duplicate_service_reviews",
            "service_review_id",
        )
        op.create_unique_constraint(
            "uq_service_review_service_student",
            "service_reviews",
            ["service_id", "student_id"],
        )


def downgrade() -> None:
    constraints = (
        (
            "service_reviews",
            "uq_service_review_service_student",
        ),
        (
            "tutor_reviews",
            "uq_tutor_review_tutor_student",
        ),
        (
            "user_role_associations",
            "uq_user_role_association",
        ),
        ("users", "uq_users_email"),
    )
    for table_name, constraint_name in constraints:
        if _has_unique_name(table_name, constraint_name):
            op.drop_constraint(constraint_name, table_name, type_="unique")
