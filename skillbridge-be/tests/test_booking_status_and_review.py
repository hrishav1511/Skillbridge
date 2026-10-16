from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from skillbridge.api.api_v1.endpoints.service_booking import get_booking_status
from skillbridge.api.repositories import review as review_repository
from skillbridge.api.repositories.review import ReviewRepository
from skillbridge.api.validators.service import CreateServiceInputValidator
from skillbridge.database.models.sqlalchemy.service_bookings import BookingStatus, ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.config import settings
from skillbridge.utils.service_time import service_datetime


def test_booking_status_is_upcoming_or_completed():
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

    assert get_booking_status(tomorrow, time(10, 0)) == "Upcoming"
    assert get_booking_status(yesterday, time(10, 0)) == "Completed"


@pytest.fixture
def review_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(review_repository, "get_session", session_context)
    return test_session


@pytest.mark.asyncio
async def test_review_is_blocked_until_booked_service_is_completed(review_session):
    student_id = uuid4()
    service = Service(
        id=uuid4(),
        tutor_id=uuid4(),
        service_name="Future session",
        date=date.today() + timedelta(days=1),
        time=time(10, 0),
        price=50,
        level=ServiceLevel.BEGINNER,
    )
    review_session.add(service)
    await review_session.flush()
    review_session.add(ServiceBooking(
        service_id=service.id, student_id=student_id,
        status=BookingStatus.ACCEPTED.value,
        scheduled_start_at=service_datetime(service.date, service.time),
    ))
    await review_session.flush()

    with pytest.raises(HTTPException) as error:
        await ReviewRepository().ensure_service_review_allowed(service.id, student_id)

    assert error.value.status_code == 400
    assert "after it is completed" in error.value.detail


@pytest.mark.asyncio
async def test_review_is_allowed_after_booked_service_is_completed(review_session):
    student_id = uuid4()
    service = Service(
        id=uuid4(),
        tutor_id=uuid4(),
        service_name="Completed session",
        date=date.today() - timedelta(days=1),
        time=time(10, 0),
        price=50,
        level=ServiceLevel.BEGINNER,
    )
    review_session.add(service)
    await review_session.flush()
    review_session.add(ServiceBooking(
        service_id=service.id, student_id=student_id,
        status=BookingStatus.ACCEPTED.value,
        scheduled_start_at=service_datetime(service.date, service.time),
    ))
    await review_session.flush()

    await ReviewRepository().ensure_service_review_allowed(service.id, student_id)


@pytest.mark.asyncio
async def test_review_is_blocked_between_service_start_and_end(review_session):
    student_id = uuid4()
    now = datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE))
    service = Service(
        id=uuid4(),
        tutor_id=uuid4(),
        service_name="Live session",
        date=now.date(),
        time=(now - timedelta(minutes=30)).time().replace(microsecond=0),
        end_time=(now + timedelta(minutes=30)).time().replace(microsecond=0),
        price=50,
        level=ServiceLevel.BEGINNER,
    )
    review_session.add(service)
    await review_session.flush()
    review_session.add(ServiceBooking(
        service_id=service.id, student_id=student_id,
        status=BookingStatus.ACCEPTED.value,
        scheduled_start_at=service_datetime(service.date, service.time),
    ))
    await review_session.flush()

    with pytest.raises(HTTPException) as error:
        await ReviewRepository().ensure_service_review_allowed(service.id, student_id)

    assert error.value.status_code == 400
    assert "after it is completed" in error.value.detail


@pytest.mark.asyncio
async def test_review_is_allowed_after_service_end_time(review_session):
    student_id = uuid4()
    now = datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE))
    service = Service(
        id=uuid4(),
        tutor_id=uuid4(),
        service_name="Finished session",
        date=now.date(),
        time=(now - timedelta(hours=2)).time().replace(microsecond=0),
        end_time=(now - timedelta(minutes=30)).time().replace(microsecond=0),
        price=50,
        level=ServiceLevel.BEGINNER,
    )
    review_session.add(service)
    await review_session.flush()
    review_session.add(ServiceBooking(
        service_id=service.id, student_id=student_id,
        status=BookingStatus.ACCEPTED.value,
        scheduled_start_at=service_datetime(service.date, service.time),
    ))
    await review_session.flush()

    await ReviewRepository().ensure_service_review_allowed(service.id, student_id)


def test_service_creation_requires_end_time_after_start_time():
    with pytest.raises(ValueError, match="end_time must be later than time"):
        CreateServiceInputValidator(
            tutor_id=uuid4(),
            service_name="Invalid session",
            description="Test",
            date=date.today() + timedelta(days=1),
            time=time(14, 0),
            end_time=time(14, 0),
            price=50,
            level=ServiceLevel.BEGINNER,
        )
