"""3rd revision: necessary tables for chat functionality

Revision ID: e326ade518ee
Revises: 52caf3672147
Create Date: 2026-06-19 15:12:48.218220

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e326ade518ee"
down_revision: Union[str, Sequence[str], None] = "52caf3672147"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "chat_rooms",
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("room_type", sa.Enum("DIRECT", "GROUP"), nullable=False),
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.CHAR(36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_chat_rooms_created_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_chat_rooms_updated_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chat_messages",
        sa.Column("chat_room_id", sa.CHAR(36), nullable=False),
        sa.Column("sender_id", sa.CHAR(36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.CHAR(36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["chat_room_id"],
            ["chat_rooms.id"],
            ondelete="CASCADE",
            name="fk_chat_messages_chat_room_id_chat_rooms",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_chat_messages_created_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_chat_messages_sender_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_chat_messages_updated_by_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_messages_chat_room_id"),
        "chat_messages",
        ["chat_room_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_messages_sender_id"), "chat_messages", ["sender_id"], unique=False
    )

    op.create_table(
        "chat_room_members",
        sa.Column("chat_room_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
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
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.CHAR(36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["chat_room_id"],
            ["chat_rooms.id"],
            ondelete="CASCADE",
            name="fk_chat_room_members_chat_room_id_chat_rooms",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_chat_room_members_created_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_chat_room_members_updated_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_chat_room_members_user_id_users",
        ),
        sa.PrimaryKeyConstraint("chat_room_id", "user_id", "id"),
    )

    op.create_table(
        "message_read_status",
        sa.Column("chat_message_id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
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
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.CHAR(36), nullable=True),
        sa.Column("updated_by_id", sa.CHAR(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["chat_message_id"],
            ["chat_messages.id"],
            ondelete="CASCADE",
            name="fk_message_read_status_chat_message_id_chat_messages",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_message_read_status_created_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_message_read_status_updated_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_message_read_status_user_id_users",
        ),
        sa.PrimaryKeyConstraint("chat_message_id", "user_id", "id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ── message_read_status ──────────────────────────────────────────────
    # Drop FK constraints first (they pin the auto-created indexes in place),
    # then the table (which drops its own PK/auto indexes cleanly).
    with op.batch_alter_table("message_read_status", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_message_read_status_chat_message_id_chat_messages", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_message_read_status_created_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_message_read_status_updated_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_message_read_status_user_id_users", type_="foreignkey"
        )
    op.drop_table("message_read_status")

    # ── chat_room_members ────────────────────────────────────────────────
    with op.batch_alter_table("chat_room_members", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_chat_room_members_chat_room_id_chat_rooms", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_chat_room_members_created_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_chat_room_members_updated_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_chat_room_members_user_id_users", type_="foreignkey"
        )
    op.drop_table("chat_room_members")

    # ── chat_messages ────────────────────────────────────────────────────
    # Drop FKs that depend on ix_chat_messages_sender_id / chat_room_id
    # BEFORE dropping those indexes explicitly.
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_chat_messages_chat_room_id_chat_rooms", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_chat_messages_created_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_chat_messages_sender_id_users", type_="foreignkey")
        batch_op.drop_constraint(
            "fk_chat_messages_updated_by_id_users", type_="foreignkey"
        )

    op.drop_index(op.f("ix_chat_messages_sender_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_chat_room_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    # ── chat_rooms ───────────────────────────────────────────────────────
    with op.batch_alter_table("chat_rooms", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_chat_rooms_created_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_chat_rooms_updated_by_id_users", type_="foreignkey"
        )
    op.drop_table("chat_rooms")
