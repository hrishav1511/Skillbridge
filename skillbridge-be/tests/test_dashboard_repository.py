from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from skillbridge.api.repositories import dashboard as dashboard_repository
from skillbridge.api.repositories.dashboard import DashboardRepository
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_bookings import BookingStatus, ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.tutor_revisions import TutorRevision
from skillbridge.database.models.sqlalchemy.service_revisions import ServiceRevision
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.config import settings
from skillbridge.utils.renderer import Status
from skillbridge.utils.service_time import service_datetime


@pytest.fixture
def dashboard_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(dashboard_repository, "get_session", session_context)
    return test_session


async def seed_dashboard_data(session):
    tutor_user = User(id=uuid4(), full_name="Tutor", email="tutor@example.com", password="x")
    student_user = User(id=uuid4(), full_name="Student", email="student@example.com", password="x")
    second_student_user = User(id=uuid4(), full_name="Second Student", email="second@example.com", password="x")
    tutor = Tutor(id=uuid4(), approval_status="ACCEPTED", is_visible=True, accepting_requests=True)
    second_tutor = Tutor(id=uuid4(), approval_status="ACCEPTED", is_visible=True, accepting_requests=True)
    student = Student(id=uuid4())
    second_student = Student(id=uuid4())
    tutor_role = Role(id=uuid4(), title="TUTOR", slug="tutor")
    student_role = Role(id=uuid4(), title="STUDENT", slug="student")
    session.add_all([
        tutor_user,
        student_user,
        second_student_user,
        tutor,
        second_tutor,
        student,
        second_student,
        tutor_role,
        student_role,
        UserRoleAssociation(user_id=tutor_user.id, role_id=tutor_role.id, tutor_id=tutor.id),
        UserRoleAssociation(user_id=student_user.id, role_id=student_role.id, student_id=student.id),
        UserRoleAssociation(user_id=second_student_user.id, role_id=student_role.id, student_id=second_student.id),
    ])

    today = datetime.now().date()
    past_service = Service(
        id=uuid4(), tutor_id=tutor.id, service_name="Past", date=today - timedelta(days=2),
        time=datetime.now().time().replace(microsecond=0), price=100, level=ServiceLevel.BEGINNER,
    )
    early_service = Service(
        id=uuid4(), tutor_id=tutor.id, service_name="Early", date=today + timedelta(days=1),
        time=datetime.now().time().replace(hour=9, minute=0, second=0, microsecond=0), price=50,
        level=ServiceLevel.BEGINNER,
    )
    late_service = Service(
        id=uuid4(), tutor_id=tutor.id, service_name="Late", date=today + timedelta(days=2),
        time=datetime.now().time().replace(hour=15, minute=0, second=0, microsecond=0), price=100,
        level=ServiceLevel.BEGINNER,
    )
    student_service = Service(
        id=uuid4(), tutor_id=second_tutor.id, service_name="Student Current Month",
        date=today, time=datetime.now().time().replace(microsecond=0), price=75, level=ServiceLevel.BEGINNER,
    )
    session.add_all([past_service, early_service, late_service, student_service])
    await session.flush()
    session.add_all([
        ServiceBooking(service_id=past_service.id, student_id=student.id, status=BookingStatus.ACCEPTED.value, scheduled_start_at=service_datetime(past_service.date, past_service.time)),
        ServiceBooking(service_id=early_service.id, student_id=student.id, status=BookingStatus.ACCEPTED.value, scheduled_start_at=service_datetime(early_service.date, early_service.time)),
        ServiceBooking(service_id=late_service.id, student_id=second_student.id, status=BookingStatus.ACCEPTED.value, scheduled_start_at=service_datetime(late_service.date, late_service.time)),
        ServiceBooking(service_id=student_service.id, student_id=student.id, status=BookingStatus.ACCEPTED.value, scheduled_start_at=service_datetime(student_service.date, student_service.time)),
        TutorReview(tutor_id=tutor.id, student_id=student.id, rating=8, created_at=datetime.now() - timedelta(days=10)),
        TutorReview(tutor_id=tutor.id, student_id=second_student.id, rating=10, created_at=datetime.now() - timedelta(days=50)),
    ])
    await session.flush()
    return tutor_user, student_user


@pytest.mark.asyncio
async def test_tutor_dashboard_metrics_and_upcoming_order(dashboard_session):
    tutor_user, _ = await seed_dashboard_data(dashboard_session)

    dashboard = await DashboardRepository().get_tutor_dashboard(tutor_user.id)

    assert dashboard.cards.total_services == 3
    assert dashboard.cards.upcoming_services == 2
    assert dashboard.cards.total_earnings == 250
    assert dashboard.cards.total_unique_students_taught == 2
    assert [item.service_name for item in dashboard.upcoming_services] == ["Early", "Late"]
    assert [item.enrolled_students_count for item in dashboard.upcoming_services] == [1, 1]
    assert dashboard.performance.average_rating == 4.5
    assert dashboard.performance.total_reviews_last_30_days == 1
    assert dashboard.performance.average_students_per_session == 1.0


@pytest.mark.asyncio
async def test_tutor_dashboard_counts_all_students_per_upcoming_session(dashboard_session):
    tutor_user, _ = await seed_dashboard_data(dashboard_session)
    early_service_id = (
        await dashboard_session.execute(
            select(Service.id).where(Service.service_name == "Early")
        )
    ).scalar_one()
    second_student_id = (
        await dashboard_session.execute(
            select(UserRoleAssociation.student_id)
            .join(User, User.id == UserRoleAssociation.user_id)
            .where(User.email == "second@example.com")
        )
    ).scalar_one()
    dashboard_session.add(
        ServiceBooking(
            service_id=early_service_id,
            student_id=second_student_id,
            status=BookingStatus.ACCEPTED.value,
            scheduled_start_at=datetime.now(ZoneInfo("UTC")) + timedelta(days=1),
        )
    )
    await dashboard_session.flush()

    dashboard = await DashboardRepository().get_tutor_dashboard(tutor_user.id)

    early_session = next(
        item for item in dashboard.upcoming_services if item.service_name == "Early"
    )
    assert early_session.enrolled_students_count == 2


@pytest.mark.asyncio
async def test_approved_unbooked_service_is_an_upcoming_tutor_session(dashboard_session):
    tutor_user, _ = await seed_dashboard_data(dashboard_session)
    tutor_id = (
        await dashboard_session.execute(
            select(UserRoleAssociation.tutor_id).where(
                UserRoleAssociation.user_id == tutor_user.id,
            )
        )
    ).scalar_one()
    service = Service(
        id=uuid4(),
        tutor_id=tutor_id,
        service_name="Approved but unbooked",
        date=datetime.now().date() + timedelta(days=3),
        time=datetime.now().time().replace(hour=11, minute=0, second=0, microsecond=0),
        price=80,
        level=ServiceLevel.BEGINNER,
    )
    dashboard_session.add(service)
    await dashboard_session.flush()

    dashboard = await DashboardRepository().get_tutor_dashboard(tutor_user.id)

    assert dashboard.cards.upcoming_services == 3
    assert any(
        item.service_name == "Approved but unbooked"
        and item.booking_id is None
        and item.enrolled_students_count == 0
        for item in dashboard.upcoming_services
    )


@pytest.mark.asyncio
async def test_student_dashboard_metrics(dashboard_session):
    _, student_user = await seed_dashboard_data(dashboard_session)

    dashboard = await DashboardRepository().get_student_dashboard(student_user.id)

    assert dashboard.total_upcoming_services == 1
    assert dashboard.total_available_tutors == 2
    assert dashboard.services_in_current_month == 3
    assert dashboard.tutors_in_current_month == 2


@pytest.mark.asyncio
async def test_admin_dashboard_returns_counts_pending_items_and_monthly_sessions(
    dashboard_session,
):
    tutor_user, student_user = await seed_dashboard_data(dashboard_session)
    tutor_id = (
        await dashboard_session.execute(
            select(UserRoleAssociation.tutor_id).where(
                UserRoleAssociation.user_id == tutor_user.id
            )
        )
    ).scalar_one()
    student_id = (
        await dashboard_session.execute(
            select(UserRoleAssociation.student_id).where(
                UserRoleAssociation.user_id == student_user.id
            )
        )
    ).scalar_one()
    tutor_revision = TutorRevision(
        id=uuid4(),
        tutor_id=tutor_id,
        academic_program="Pending",
        approval_status=Status.PENDING,
        revision_type="UPDATE",
    )
    service_revision = ServiceRevision(
        id=uuid4(),
        tutor_id=tutor_id,
        service_name="Pending service",
        date=datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE)).date(),
        time=datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE)).time().replace(microsecond=0),
        price=20,
        level=ServiceLevel.BEGINNER,
        approval_status=Status.PENDING,
        revision_type="CREATE",
    )
    dashboard_session.add_all([tutor_revision, service_revision])
    await dashboard_session.flush()

    dashboard = await DashboardRepository().get_admin_dashboard()

    assert dashboard.total_students == 2
    assert dashboard.total_tutors == 2
    assert dashboard.total_services == 4
    assert dashboard.pending_items == 2
    assert len(dashboard.monthly_services_done) == 12
    assert all(item.month and item.services_done >= 0 for item in dashboard.monthly_services_done)
