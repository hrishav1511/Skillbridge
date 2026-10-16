"""Add session workflow, rescheduling, and reported reviews.

Revision ID: a81d2f3c4b5e
Revises: 7ac91e2d4f60
Create Date: 2026-09-19 18:00:00.000000
"""

from typing import Sequence, Union
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from alembic import context, op
import sqlalchemy as sa

revision: str = "a81d2f3c4b5e"
down_revision: Union[str, Sequence[str], None] = "7ac91e2d4f60"
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


def _columns(table_name: str):
    if _is_offline_mode():
        if table_name == "chat_messages":
            return {}
        if table_name == "service_bookings":
            return {
                "status": {
                    "name": "status",
                    "nullable": True,
                    "type": sa.String(length=50),
                    "default": None,
                }
            }
    return {column["name"]: column for column in _inspector().get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    if _is_offline_mode():
        return False
    return any(
        index["name"] == index_name for index in _inspector().get_indexes(table_name)
    )


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


def _has_foreign_key_columns(table_name: str, column_names: Sequence[str]) -> bool:
    if _is_offline_mode():
        return False
    expected = tuple(column_names)
    return any(
        tuple(foreign_key.get("constrained_columns") or ()) == expected
        for foreign_key in _inspector().get_foreign_keys(table_name)
    )


def _has_check(table_name: str, constraint_name: str) -> bool:
    if _is_offline_mode():
        return False
    return any(
        constraint.get("name") == constraint_name
        for constraint in _inspector().get_check_constraints(table_name)
    )


def _base_columns(include_audit_users: bool = False):
    columns = [
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
    ]
    if include_audit_users:
        columns.extend(
            [
                sa.Column("created_by_id", sa.CHAR(length=36), nullable=True),
                sa.Column("updated_by_id", sa.CHAR(length=36), nullable=True),
            ]
        )
    return columns


def _backfill_scheduled_start_at() -> None:
    if _is_offline_mode():
        op.execute(
            "UPDATE service_bookings AS sb "
            "INNER JOIN services AS s ON s.id = sb.service_id "
            "SET sb.scheduled_start_at = "
            "CONVERT_TZ(TIMESTAMP(s.date, s.time), 'Europe/Berlin', '+00:00') "
            "WHERE sb.scheduled_start_at IS NULL"
        )
        return

    bookings = sa.table(
        "service_bookings",
        sa.column("id", sa.CHAR(length=36)),
        sa.column("service_id", sa.CHAR(length=36)),
        sa.column("scheduled_start_at", sa.DateTime()),
    )
    services = sa.table(
        "services",
        sa.column("id", sa.CHAR(length=36)),
        sa.column("date", sa.Date()),
        sa.column("time", sa.Time()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(bookings.c.id, services.c.date, services.c.time)
        .select_from(bookings.join(services, services.c.id == bookings.c.service_id))
        .where(bookings.c.scheduled_start_at.is_(None))
    )
    local_zone = ZoneInfo("Europe/Berlin")
    for booking_id, service_date, service_time in rows:
        utc_start = (
            datetime.combine(service_date, service_time, tzinfo=local_zone)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
        connection.execute(
            bookings.update()
            .where(bookings.c.id == booking_id)
            .values(scheduled_start_at=utc_start)
        )


def upgrade() -> None:
    # Current model metadata may have been applied by create_all(), and MySQL
    # can retain completed DDL after a later statement fails. Reconcile each
    # object so this revision is safe both after bootstrap and on retry.
    if "client_message_id" not in _columns("chat_messages"):
        op.add_column(
            "chat_messages",
            sa.Column("client_message_id", sa.CHAR(length=36), nullable=True),
        )
    if not _has_index("chat_messages", "ix_chat_messages_client_message_id"):
        op.create_index(
            "ix_chat_messages_client_message_id",
            "chat_messages",
            ["client_message_id"],
            unique=False,
        )
    if not _has_unique_columns("chat_messages", ["sender_id", "client_message_id"]):
        op.create_unique_constraint(
            "uq_chat_message_sender_client_id",
            "chat_messages",
            ["sender_id", "client_message_id"],
        )

    # Legacy bookings represented completed booking actions and had no request
    # lifecycle. They are therefore preserved as ACCEPTED rather than being
    # incorrectly turned into new pending requests.
    booking_columns = _columns("service_bookings")
    status_column = booking_columns["status"]
    status_length = getattr(status_column["type"], "length", None)
    status_default = str(status_column.get("default") or "").strip("'").upper()
    if status_length != 20 or status_column["nullable"] or status_default != "PENDING":
        op.execute(
            "UPDATE service_bookings SET status = 'ACCEPTED' "
            "WHERE status IS NULL OR status NOT IN "
            "('PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED')"
        )
        op.alter_column(
            "service_bookings",
            "status",
            existing_type=status_column["type"],
            type_=sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        )

    if "scheduled_start_at" not in booking_columns:
        op.add_column(
            "service_bookings",
            sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
        )
    if _is_offline_mode():
        scheduled_start = {"nullable": True, "type": sa.DateTime(timezone=True)}
    else:
        scheduled_start = _columns("service_bookings")["scheduled_start_at"]
    if scheduled_start["nullable"]:
        _backfill_scheduled_start_at()
        op.alter_column(
            "service_bookings",
            "scheduled_start_at",
            existing_type=scheduled_start["type"],
            nullable=False,
        )

    booking_columns = _columns("service_bookings")
    if "status_updated_at" not in booking_columns:
        op.add_column(
            "service_bookings",
            sa.Column(
                "status_updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )
    if "cancelled_at" not in booking_columns:
        op.add_column(
            "service_bookings",
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "cancelled_by_user_id" not in booking_columns:
        op.add_column(
            "service_bookings",
            sa.Column("cancelled_by_user_id", sa.CHAR(length=36), nullable=True),
        )
    if "cancellation_reason" not in booking_columns:
        op.add_column(
            "service_bookings",
            sa.Column("cancellation_reason", sa.String(length=512), nullable=True),
        )
    if not _has_foreign_key_columns("service_bookings", ["cancelled_by_user_id"]):
        op.create_foreign_key(
            "fk_service_bookings_cancelled_by_user",
            "service_bookings",
            "users",
            ["cancelled_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_check("service_bookings", "ck_service_bookings_status"):
        op.create_check_constraint(
            "ck_service_bookings_status",
            "service_bookings",
            "status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED')",
        )
    if not _has_index("service_bookings", "ix_service_bookings_status"):
        op.create_index(
            "ix_service_bookings_status",
            "service_bookings",
            ["status"],
            unique=False,
        )
    if not _has_index("service_bookings", "ix_service_bookings_scheduled_start"):
        op.create_index(
            "ix_service_bookings_scheduled_start",
            "service_bookings",
            ["scheduled_start_at"],
            unique=False,
        )

    if not _has_table("booking_reschedule_proposals"):
        op.create_table(
            "booking_reschedule_proposals",
            *_base_columns(),
            sa.Column("booking_id", sa.CHAR(length=36), nullable=False),
            sa.Column("proposed_by_user_id", sa.CHAR(length=36), nullable=False),
            sa.Column("previous_start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("proposed_start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "proposal_status",
                sa.String(length=20),
                server_default="PENDING",
                nullable=False,
            ),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("responded_by_user_id", sa.CHAR(length=36), nullable=True),
            sa.CheckConstraint(
                "proposal_status IN ('PENDING', 'ACCEPTED', 'REJECTED')",
                name="ck_booking_reschedule_proposal_status",
            ),
            sa.ForeignKeyConstraint(
                ["booking_id"], ["service_bookings.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["proposed_by_user_id"], ["users.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["responded_by_user_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(
        "booking_reschedule_proposals", "ix_booking_reschedule_booking_created"
    ):
        op.create_index(
            "ix_booking_reschedule_booking_created",
            "booking_reschedule_proposals",
            ["booking_id", "created_at"],
            unique=False,
        )
    if not _has_index(
        "booking_reschedule_proposals", "ix_booking_reschedule_booking_status"
    ):
        op.create_index(
            "ix_booking_reschedule_booking_status",
            "booking_reschedule_proposals",
            ["booking_id", "proposal_status"],
            unique=False,
        )

    if not _has_table("reported_reviews"):
        op.create_table(
            "reported_reviews",
            *_base_columns(include_audit_users=True),
            sa.Column("reporter_user_id", sa.CHAR(length=36), nullable=False),
            sa.Column("tutor_review_id", sa.CHAR(length=36), nullable=True),
            sa.Column("service_review_id", sa.CHAR(length=36), nullable=True),
            sa.Column("reason", sa.String(length=1024), nullable=False),
            sa.Column(
                "reported_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "(tutor_review_id IS NOT NULL AND service_review_id IS NULL) OR "
                "(tutor_review_id IS NULL AND service_review_id IS NOT NULL)",
                name="ck_reported_reviews_exact_target",
            ),
            sa.ForeignKeyConstraint(
                ["reporter_user_id"], ["users.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["tutor_review_id"], ["tutor_reviews.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["service_review_id"], ["service_reviews.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["created_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["updated_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "reporter_user_id",
                "tutor_review_id",
                name="uq_reported_tutor_review_reporter",
            ),
            sa.UniqueConstraint(
                "reporter_user_id",
                "service_review_id",
                name="uq_reported_service_review_reporter",
            ),
        )
    if not _has_index("reported_reviews", "ix_reported_reviews_reported_at"):
        op.create_index(
            "ix_reported_reviews_reported_at",
            "reported_reviews",
            ["reported_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_reported_reviews_reported_at", table_name="reported_reviews")
    op.drop_table("reported_reviews")
    op.drop_index(
        "ix_booking_reschedule_booking_status",
        table_name="booking_reschedule_proposals",
    )
    op.drop_index(
        "ix_booking_reschedule_booking_created",
        table_name="booking_reschedule_proposals",
    )
    op.drop_table("booking_reschedule_proposals")
    op.drop_index("ix_service_bookings_scheduled_start", table_name="service_bookings")
    op.drop_index("ix_service_bookings_status", table_name="service_bookings")
    op.drop_constraint("ck_service_bookings_status", "service_bookings", type_="check")
    op.drop_constraint(
        "fk_service_bookings_cancelled_by_user",
        "service_bookings",
        type_="foreignkey",
    )
    op.drop_column("service_bookings", "cancellation_reason")
    op.drop_column("service_bookings", "cancelled_by_user_id")
    op.drop_column("service_bookings", "cancelled_at")
    op.drop_column("service_bookings", "status_updated_at")
    op.drop_column("service_bookings", "scheduled_start_at")
    op.execute(
        "UPDATE service_bookings SET status = 'ACTIVE' "
        "WHERE status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED')"
    )
    op.alter_column(
        "service_bookings",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=50),
        nullable=True,
        server_default=None,
    )
    op.drop_constraint(
        "uq_chat_message_sender_client_id", "chat_messages", type_="unique"
    )
    op.drop_index("ix_chat_messages_client_message_id", table_name="chat_messages")
    op.drop_column("chat_messages", "client_message_id")
