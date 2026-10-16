from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from skillbridge.config import settings
from skillbridge.api.validators.service import ServiceScheduleStatus


def service_datetime(service_date: date, service_time: time) -> datetime:
    """Convert a stored local service date/time to an aware UTC datetime."""
    local_datetime = datetime.combine(
        service_date,
        service_time,
        tzinfo=ZoneInfo(settings.SERVICE_TIMEZONE),
    )
    return local_datetime.astimezone(timezone.utc)


def get_service_schedule_status(
    service_date: date,
    start_time: time,
    end_time: time | None = None,
) -> ServiceScheduleStatus:
    now = datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE))
    start = datetime.combine(
        service_date,
        start_time,
        tzinfo=ZoneInfo(settings.SERVICE_TIMEZONE),
    )
    end = datetime.combine(
        service_date,
        end_time or start_time,
        tzinfo=ZoneInfo(settings.SERVICE_TIMEZONE),
    )
    if now < start:
        return ServiceScheduleStatus.UPCOMING
    if now < end:
        return ServiceScheduleStatus.RUNNING
    return ServiceScheduleStatus.COMPLETED


def get_scheduled_status(
    scheduled_start_at: datetime,
    original_start_time: time,
    original_end_time: time | None = None,
) -> ServiceScheduleStatus:
    """Return status using the reschedulable UTC start and original duration."""
    if scheduled_start_at.tzinfo is None:
        start = scheduled_start_at.replace(tzinfo=timezone.utc)
    else:
        start = scheduled_start_at.astimezone(timezone.utc)
    duration = datetime.combine(
        date.min, original_end_time or original_start_time
    ) - datetime.combine(date.min, original_start_time)
    end = start + max(duration, timedelta(0))
    now = datetime.now(timezone.utc)
    if now < start:
        return ServiceScheduleStatus.UPCOMING
    if now < end:
        return ServiceScheduleStatus.RUNNING
    return ServiceScheduleStatus.COMPLETED


def utc_isoformat(value: datetime | None) -> str | None:
    """Render a stored datetime as ISO-8601 with an explicit UTC offset.

    MySQL hands back naive datetimes even for `DateTime(timezone=True)` columns.
    Serialising those with `.isoformat()` produces a string with no offset, which
    browsers parse as *local* time - so a UTC timestamp renders shifted by the
    viewer's offset. Stored values are UTC, so label them as such and let the
    client convert.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
