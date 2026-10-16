import importlib.util
from pathlib import Path

import sqlalchemy as sa

VERSIONS_DIR = (
    Path(__file__).parent.parent
    / "src"
    / "skillbridge"
    / "database"
    / "alembic"
    / "versions"
)


def _load_migration(filename: str):
    path = VERSIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _RecordingOperations:
    def __init__(self):
        self.calls = []

    def get_bind(self):
        return object()

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return record


class _CurrentSchemaInspector:
    tables = {
        "reported_tutors",
        "reported_services",
        "booking_reschedule_proposals",
        "reported_reviews",
    }

    indexes = {
        "users": [
            {"name": "ix_users_email", "column_names": ["email"], "unique": True}
        ],
        "chat_messages": [
            {
                "name": "ix_chat_messages_client_message_id",
                "column_names": ["client_message_id"],
                "unique": False,
            }
        ],
        "service_bookings": [
            {"name": "ix_service_bookings_status", "column_names": ["status"]},
            {
                "name": "ix_service_bookings_scheduled_start",
                "column_names": ["scheduled_start_at"],
            },
        ],
        "booking_reschedule_proposals": [
            {
                "name": "ix_booking_reschedule_booking_created",
                "column_names": ["booking_id", "created_at"],
            },
            {
                "name": "ix_booking_reschedule_booking_status",
                "column_names": ["booking_id", "proposal_status"],
            },
        ],
        "reported_reviews": [
            {
                "name": "ix_reported_reviews_reported_at",
                "column_names": ["reported_at"],
            }
        ],
    }

    unique_constraints = {
        "users": [{"column_names": ["email"]}],
        "user_role_associations": [{"column_names": ["user_id", "role_id"]}],
        "tutor_reviews": [{"column_names": ["tutor_id", "student_id"]}],
        "service_reviews": [{"column_names": ["service_id", "student_id"]}],
        "chat_messages": [{"column_names": ["sender_id", "client_message_id"]}],
    }

    def has_table(self, table_name):
        return table_name in self.tables

    def get_indexes(self, table_name):
        return self.indexes.get(table_name, [])

    def get_unique_constraints(self, table_name):
        return self.unique_constraints.get(table_name, [])

    def get_columns(self, table_name):
        if table_name == "users":
            return [{"name": "email", "nullable": False}]
        if table_name == "chat_messages":
            return [{"name": "client_message_id", "nullable": True}]
        if table_name == "service_bookings":
            return [
                {
                    "name": "status",
                    "nullable": False,
                    "type": sa.String(20),
                    "default": "'PENDING'",
                },
                {
                    "name": "scheduled_start_at",
                    "nullable": False,
                    "type": sa.DateTime(),
                },
                {"name": "status_updated_at"},
                {"name": "cancelled_at"},
                {"name": "cancelled_by_user_id"},
                {"name": "cancellation_reason"},
            ]
        raise AssertionError(f"Unexpected table inspection: {table_name}")

    def get_foreign_keys(self, table_name):
        assert table_name == "service_bookings"
        return [{"constrained_columns": ["cancelled_by_user_id"]}]

    def get_check_constraints(self, table_name):
        assert table_name == "service_bookings"
        return [{"name": "ck_service_bookings_status"}]


def test_security_reporting_migration_accepts_precreated_schema(monkeypatch):
    migration = _load_migration(
        "2026_09_19_1200-7ac91e2d4f60_security_and_reporting.py"
    )
    operations = _RecordingOperations()
    inspector = _CurrentSchemaInspector()
    migration.op = operations
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)

    migration.upgrade()

    assert operations.calls == []


def test_security_reporting_migration_resumes_after_first_table(monkeypatch):
    migration = _load_migration(
        "2026_09_19_1200-7ac91e2d4f60_security_and_reporting.py"
    )
    operations = _RecordingOperations()
    inspector = _CurrentSchemaInspector()
    inspector.tables = {"reported_tutors"}
    migration.op = operations
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)

    migration.upgrade()

    assert [(name, args[0]) for name, args, _ in operations.calls] == [
        ("create_table", "reported_services")
    ]


def test_session_workflow_migration_accepts_precreated_schema(monkeypatch):
    migration = _load_migration(
        "2026_09_19_1800-a81d2f3c4b5e_session_workflow_and_review_reports.py"
    )
    operations = _RecordingOperations()
    inspector = _CurrentSchemaInspector()
    migration.op = operations
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)

    migration.upgrade()

    assert operations.calls == []


def test_deduplication_migration_accepts_existing_unique_keys(monkeypatch):
    migration = _load_migration(
        "2026_09_19_2000-b92e4a6d7c8f_deduplicate_security_keys.py"
    )
    operations = _RecordingOperations()
    inspector = _CurrentSchemaInspector()
    migration.op = operations
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)

    migration.upgrade()

    assert operations.calls == []
