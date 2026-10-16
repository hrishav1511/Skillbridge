"""12th migration: refresh token table and review tables

Revision ID: d21d0d18fba7
Revises: 6be5d8f6ed76
Create Date: 2026-08-17 20:00:59.528638

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d21d0d18fba7"
down_revision: Union[str, Sequence[str], None] = "6be5d8f6ed76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_by_id", sa.CHAR(36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(36), nullable=True),

        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_refresh_tokens_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name="fk_refresh_tokens_updated_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user",
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    # ------------------------------------------------------------------
    # service_reviews
    # Change student_id FK from users.id -> students.id
    # ------------------------------------------------------------------

    op.drop_constraint(
        op.f("service_reviews_ibfk_3"),
        "service_reviews",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_service_reviews_student",
        "service_reviews",
        "students",
        ["student_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------
    # service_revisions
    # ------------------------------------------------------------------

    op.add_column(
        "service_revisions",
        sa.Column("tags", sa.JSON(), nullable=True),
    )

    # ------------------------------------------------------------------
    # tutor_reviews
    # Change student_id FK from users.id -> students.id
    # ------------------------------------------------------------------

    op.drop_constraint(
        op.f("tutor_reviews_ibfk_2"),
        "tutor_reviews",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_tutor_reviews_student",
        "tutor_reviews",
        "students",
        ["student_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------
    # tutor_revisions
    # ------------------------------------------------------------------

    op.add_column(
        "tutor_revisions",
        sa.Column("tags", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""

    # ------------------------------------------------------------------
    # tutor_revisions
    # ------------------------------------------------------------------

    op.drop_column(
        "tutor_revisions",
        "tags",
    )

    # ------------------------------------------------------------------
    # tutor_reviews
    # Restore student_id FK: students.id -> users.id
    # ------------------------------------------------------------------

    op.drop_constraint(
        "fk_tutor_reviews_student",
        "tutor_reviews",
        type_="foreignkey",
    )

    op.create_foreign_key(
        op.f("tutor_reviews_ibfk_2"),
        "tutor_reviews",
        "users",
        ["student_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------
    # service_revisions
    # ------------------------------------------------------------------

    op.drop_column(
        "service_revisions",
        "tags",
    )

    # ------------------------------------------------------------------
    # service_reviews
    # Restore student_id FK: students.id -> users.id
    # ------------------------------------------------------------------

    op.drop_constraint(
        "fk_service_reviews_student",
        "service_reviews",
        type_="foreignkey",
    )

    op.create_foreign_key(
        op.f("service_reviews_ibfk_3"),
        "service_reviews",
        "users",
        ["student_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------
    # refresh_tokens
    # ------------------------------------------------------------------

    op.drop_table("refresh_tokens")