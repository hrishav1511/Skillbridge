from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from skillbridge.api.filters.service import ServiceSearchFilter
from skillbridge.api.validators.service import ServiceSearchValidator, ServiceScheduleStatus
from skillbridge.config import settings
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.utils.service_time import get_service_schedule_status


@pytest.fixture
def service_filter_now():
    return datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE)).replace(microsecond=0)


def test_service_schedule_status_is_computed_for_response_data(service_filter_now):
    now = service_filter_now

    assert (
        get_service_schedule_status(
            (now + timedelta(days=1)).date(),
            now.time(),
            (now + timedelta(days=1, minutes=30)).time(),
        )
        == ServiceScheduleStatus.UPCOMING
    )
    assert (
        get_service_schedule_status(
            now.date(),
            (now - timedelta(minutes=30)).time(),
            (now + timedelta(minutes=30)).time(),
        )
        == ServiceScheduleStatus.RUNNING
    )
    assert (
        get_service_schedule_status(
            now.date(),
            (now - timedelta(hours=2)).time(),
            (now - timedelta(minutes=30)).time(),
        )
        == ServiceScheduleStatus.COMPLETED
    )


async def _query_service_ids(session, **criteria):
    search = await ServiceSearchFilter(ServiceSearchValidator(**criteria))
    query = await search.get_query()
    result = await session.execute(query)
    return {service.id for service in result.scalars().unique().all()}


@pytest.mark.asyncio
async def test_services_can_be_filtered_by_tutor_and_schedule_status(
    test_session, service_filter_now
):
    now = service_filter_now
    tutor_id = uuid4()
    other_tutor_id = uuid4()
    upcoming = Service(
        id=uuid4(),
        tutor_id=tutor_id,
        service_name="Upcoming",
        date=(now + timedelta(days=1)).date(),
        time=now.time(),
        end_time=(now + timedelta(days=1, minutes=30)).time(),
        price=10,
        level=ServiceLevel.BEGINNER,
    )
    running = Service(
        id=uuid4(),
        tutor_id=tutor_id,
        service_name="Running",
        date=now.date(),
        time=(now - timedelta(minutes=30)).time(),
        end_time=(now + timedelta(minutes=30)).time(),
        price=10,
        level=ServiceLevel.BEGINNER,
    )
    completed = Service(
        id=uuid4(),
        tutor_id=other_tutor_id,
        service_name="Completed",
        date=now.date(),
        time=(now - timedelta(hours=2)).time(),
        end_time=(now - timedelta(minutes=30)).time(),
        price=10,
        level=ServiceLevel.BEGINNER,
    )
    test_session.add_all([upcoming, running, completed])
    await test_session.flush()

    assert await _query_service_ids(
        test_session,
        tutor_id=tutor_id,
        schedule_status=ServiceScheduleStatus.UPCOMING,
    ) == {upcoming.id}
    assert await _query_service_ids(
        test_session,
        tutor_id=tutor_id,
        schedule_status=ServiceScheduleStatus.RUNNING,
    ) == {running.id}
    assert await _query_service_ids(
        test_session,
        schedule_status=ServiceScheduleStatus.COMPLETED,
    ) == {completed.id}


@pytest.mark.asyncio
async def test_legacy_service_without_end_time_is_completed_after_start(
    test_session, service_filter_now
):
    now = service_filter_now
    legacy_service = Service(
        id=uuid4(),
        tutor_id=uuid4(),
        service_name="Legacy service",
        date=(now - timedelta(minutes=1)).date(),
        time=(now - timedelta(minutes=1)).time(),
        end_time=None,
        price=10,
        level=ServiceLevel.BEGINNER,
    )
    test_session.add(legacy_service)
    await test_session.flush()

    result = await _query_service_ids(
        test_session,
        schedule_status=ServiceScheduleStatus.COMPLETED,
    )

    assert result == {legacy_service.id}


@pytest.mark.asyncio
async def test_service_filter_supports_price_range_and_price_sort():
    search = await ServiceSearchFilter(
        ServiceSearchValidator(min_price=25, max_price=100, sort="price:asc")
    )

    assert len(search._filters) == 2
    assert search.get_sorting_orders()
