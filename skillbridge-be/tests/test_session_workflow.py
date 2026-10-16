from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from skillbridge.api.repositories import service_booking as booking_repository
from skillbridge.api.repositories.service_booking import ServiceBookingRepository
from skillbridge.api.validators.service import CreateServiceBookingInputValidator
from skillbridge.database.models.sqlalchemy.booking_reschedule_proposals import RescheduleProposalStatus
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_bookings import (
    ALLOWED_BOOKING_TRANSITIONS,
    BookingStatus,
    ServiceBooking,
    booking_transition_allowed,
)
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import BaseExceptionMixin
from skillbridge.utils.service_time import service_datetime


@pytest.fixture
def workflow_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(booking_repository, "get_session", session_context)
    return test_session


async def _seed_participants(session):
    tutor_user = User(id=uuid4(), full_name="Tutor", email="tutor@hs-fulda.de", password="x")
    student_user = User(id=uuid4(), full_name="Student", email="student@hs-fulda.de", password="x")
    other_user = User(id=uuid4(), full_name="Other", email="other@hs-fulda.de", password="x")
    tutor = Tutor(
        id=uuid4(), approval_status="ACCEPTED", is_visible=True,
        accepting_requests=True, status="ACTIVE",
    )
    student = Student(id=uuid4())
    other_student = Student(id=uuid4())
    tutor_role = Role(id=uuid4(), title="Tutor", slug="tutor")
    student_role = Role(id=uuid4(), title="Student", slug="student")
    service = Service(
        id=uuid4(), tutor_id=tutor.id, service_name="Python",
        date=date.today() + timedelta(days=4), time=time(10), end_time=time(11),
        price=20, level=ServiceLevel.BEGINNER, status="ACTIVE",
    )
    session.add_all([
        tutor_user, student_user, other_user, tutor, student, other_student,
        tutor_role, student_role, service,
        UserRoleAssociation(user_id=tutor_user.id, role_id=tutor_role.id, tutor_id=tutor.id),
        UserRoleAssociation(user_id=student_user.id, role_id=student_role.id, student_id=student.id),
        UserRoleAssociation(user_id=other_user.id, role_id=student_role.id, student_id=other_student.id),
    ])
    await session.flush()
    return tutor_user, student_user, other_user, tutor, student, service


@pytest.mark.asyncio
async def test_session_request_accept_and_notification_flow(workflow_session):
    tutor_user, student_user, other_user, _, student, service = await _seed_participants(workflow_session)
    repository = ServiceBookingRepository()

    created = await repository.create_service_booking(
        CreateServiceBookingInputValidator(service_id=service.id, student_id=student.id)
    )
    booking = created["data"]
    assert booking.status == BookingStatus.PENDING.value
    assert booking.scheduled_start_at == service_datetime(service.date, service.time).replace(tzinfo=None)
    assert (await workflow_session.execute(
        select(Notification).where(
            Notification.user_id == tutor_user.id,
            Notification.notification_type == "SESSION_REQUESTED",
        )
    )).scalar_one()

    assert (await repository.get_booking_for_user(booking.id, student_user.id)).id == booking.id
    assert (await repository.get_booking_for_user(booking.id, tutor_user.id)).id == booking.id
    with pytest.raises(BaseExceptionMixin) as forbidden:
        await repository.get_booking_for_user(booking.id, other_user.id)
    assert forbidden.value.status_code == 403

    accepted = await repository.accept_booking(booking.id, tutor_user.id)
    assert accepted["data"].status == BookingStatus.ACCEPTED.value
    assert (await workflow_session.execute(
        select(Notification).where(
            Notification.user_id == student_user.id,
            Notification.notification_type == "SESSION_ACCEPTED",
        )
    )).scalar_one()

    with pytest.raises(BaseExceptionMixin) as second_accept:
        await repository.accept_booking(booking.id, tutor_user.id)
    assert second_accept.value.status_code == 409


@pytest.mark.asyncio
async def test_declined_and_cancelled_states_are_terminal(workflow_session):
    tutor_user, student_user, _, _, student, service = await _seed_participants(workflow_session)
    repository = ServiceBookingRepository()
    booking = (await repository.create_service_booking(
        CreateServiceBookingInputValidator(service_id=service.id, student_id=student.id)
    ))["data"]

    declined = await repository.decline_booking(booking.id, tutor_user.id)
    assert declined["data"].status == BookingStatus.DECLINED.value
    assert (await workflow_session.execute(
        select(Notification).where(
            Notification.user_id == student_user.id,
            Notification.notification_type == "SESSION_DECLINED",
        )
    )).scalar_one()
    with pytest.raises(BaseExceptionMixin) as accept_declined:
        await repository.accept_booking(booking.id, tutor_user.id)
    assert accept_declined.value.status_code == 409
    with pytest.raises(BaseExceptionMixin) as cancel_declined:
        await repository.cancel_service_booking(booking.id, student_user.id)
    assert cancel_declined.value.status_code == 409


def test_booking_transition_matrix_is_complete():
    for current, allowed_targets in ALLOWED_BOOKING_TRANSITIONS.items():
        for target in BookingStatus:
            expected = target in allowed_targets
            assert booking_transition_allowed(current.value, target) is expected


@pytest.mark.asyncio
async def test_reschedule_requires_other_participant_and_persists_history(workflow_session):
    tutor_user, student_user, other_user, _, student, service = await _seed_participants(workflow_session)
    repository = ServiceBookingRepository()
    booking = (await repository.create_service_booking(
        CreateServiceBookingInputValidator(service_id=service.id, student_id=student.id)
    ))["data"]
    await repository.accept_booking(booking.id, tutor_user.id)

    proposed_time = datetime.now(timezone.utc) + timedelta(days=7)
    proposal = await repository.propose_reschedule(
        booking.id, student_user.id, proposed_time
    )
    assert proposal.proposal_status == RescheduleProposalStatus.PENDING.value
    assert booking.scheduled_start_at != proposal.proposed_start_at

    with pytest.raises(BaseExceptionMixin) as own_response:
        await repository.respond_to_reschedule(
            booking.id, proposal.id, student_user.id, accept=True
        )
    assert own_response.value.status_code == 403
    with pytest.raises(BaseExceptionMixin) as unrelated_proposal:
        await repository.propose_reschedule(booking.id, other_user.id, proposed_time)
    assert unrelated_proposal.value.status_code == 403

    accepted = await repository.respond_to_reschedule(
        booking.id, proposal.id, tutor_user.id, accept=True
    )
    assert accepted.proposal_status == RescheduleProposalStatus.ACCEPTED.value
    await workflow_session.refresh(booking)
    assert booking.scheduled_start_at == proposed_time.replace(tzinfo=None)
    with pytest.raises(BaseExceptionMixin) as second_response:
        await repository.respond_to_reschedule(
            booking.id, proposal.id, tutor_user.id, accept=False
        )
    assert second_response.value.status_code == 409

    tutor_proposal_time = proposed_time + timedelta(days=1)
    tutor_proposal = await repository.propose_reschedule(
        booking.id, tutor_user.id, tutor_proposal_time
    )
    before_rejection = booking.scheduled_start_at
    rejected = await repository.respond_to_reschedule(
        booking.id, tutor_proposal.id, student_user.id, accept=False
    )
    assert rejected.proposal_status == RescheduleProposalStatus.REJECTED.value
    await workflow_session.refresh(booking)
    assert booking.scheduled_start_at == before_rejection

    history = await repository.list_reschedule_history(booking.id, student_user.id)
    assert [item.proposal_status for item in history] == [
        RescheduleProposalStatus.REJECTED.value,
        RescheduleProposalStatus.ACCEPTED.value,
    ]
    notification_types = set((await workflow_session.execute(
        select(Notification.notification_type)
    )).scalars().all())
    assert {
        "RESCHEDULE_PROPOSED",
        "RESCHEDULE_ACCEPTED",
        "RESCHEDULE_REJECTED",
    }.issubset(notification_types)
