from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from skillbridge.api.repositories import service_booking as booking_repository
from skillbridge.api.repositories.service_booking import ServiceBookingRepository
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.booking_reschedule_proposals import (
    BookingRescheduleProposal,
    RescheduleProposalStatus,
)
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.service_bookings import (
    BookingStatus,
    ServiceBooking,
)
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import BaseExceptionMixin
from skillbridge.utils.service_time import service_datetime


@pytest.fixture
def booking_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(booking_repository, "get_session", session_context)
    return test_session


async def _seed_booking(session, service_date, booking_status=BookingStatus.ACCEPTED):
    tutor_user = User(
        id=uuid4(), full_name="Tutor", email=f"{uuid4()}@example.com", password="x"
    )
    student_user = User(
        id=uuid4(), full_name="Student", email=f"{uuid4()}@example.com", password="x"
    )
    tutor = Tutor(
        id=uuid4(), approval_status="ACCEPTED", is_visible=True, accepting_requests=True
    )
    student = Student(id=uuid4())
    tutor_role = Role(id=uuid4(), title="Tutor", slug="tutor")
    student_role = Role(id=uuid4(), title="Student", slug="student")
    service = Service(
        id=uuid4(),
        tutor_id=tutor.id,
        service_name="Python",
        date=service_date,
        time=time(10, 0),
        end_time=time(11, 0),
        price=20,
        level=ServiceLevel.BEGINNER,
    )
    booking = ServiceBooking(
        id=uuid4(),
        service_id=service.id,
        student_id=student.id,
        status=booking_status.value,
        scheduled_start_at=service_datetime(service.date, service.time),
    )
    session.add_all(
        [
            tutor_user,
            student_user,
            tutor,
            student,
            tutor_role,
            student_role,
            service,
            booking,
            UserRoleAssociation(
                user_id=tutor_user.id, role_id=tutor_role.id, tutor_id=tutor.id
            ),
            UserRoleAssociation(
                user_id=student_user.id, role_id=student_role.id, student_id=student.id
            ),
        ]
    )
    await session.flush()
    return booking, student_user, tutor_user


@pytest.mark.asyncio
async def test_student_cancellation_preserves_history(booking_session):
    booking, student_user, tutor_user = await _seed_booking(
        booking_session, date.today() + timedelta(days=1)
    )

    proposal = BookingRescheduleProposal(
        booking_id=booking.id,
        proposed_by_user_id=student_user.id,
        previous_start_at=booking.scheduled_start_at,
        proposed_start_at=datetime.now(timezone.utc) + timedelta(days=2),
        proposal_status=RescheduleProposalStatus.PENDING.value,
    )
    booking_session.add(proposal)
    await booking_session.flush()

    result = await ServiceBookingRepository().cancel_service_booking(
        booking.id, student_user.id, "Schedule conflict"
    )

    assert result["success"] is True
    persisted = await booking_session.get(ServiceBooking, booking.id)
    assert persisted is not None
    assert persisted.status == BookingStatus.CANCELLED.value
    assert persisted.cancellation_reason == "Schedule conflict"
    await booking_session.refresh(proposal)
    assert proposal.proposal_status == RescheduleProposalStatus.REJECTED.value
    assert proposal.responded_by_user_id == student_user.id
    cancellation_notice = (
        await booking_session.execute(
            select(Notification).where(
                Notification.user_id == tutor_user.id,
                Notification.notification_type == "SESSION_CANCELLED",
            )
        )
    ).scalar_one()
    assert cancellation_notice.data["booking_id"] == str(booking.id)


@pytest.mark.asyncio
async def test_unrelated_user_cannot_cancel_booking(booking_session):
    booking, _, _ = await _seed_booking(
        booking_session, date.today() + timedelta(days=1)
    )

    with pytest.raises(BaseExceptionMixin) as error:
        await ServiceBookingRepository().cancel_service_booking(booking.id, uuid4())

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_completed_booking_cannot_be_cancelled(booking_session):
    booking, student_user, _ = await _seed_booking(
        booking_session, date.today() - timedelta(days=1)
    )

    with pytest.raises(BaseExceptionMixin) as error:
        await ServiceBookingRepository().cancel_service_booking(
            booking.id, student_user.id
        )

    assert error.value.status_code == 409
    assert "completed" in error.value.message
