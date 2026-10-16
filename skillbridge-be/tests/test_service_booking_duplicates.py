from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from skillbridge.database.models.sqlalchemy.service_bookings import ServiceBooking


@pytest.mark.asyncio
async def test_service_booking_unique_constraint_rejects_duplicate(test_session):
    service_id = uuid4()
    student_id = uuid4()
    test_session.add(
        ServiceBooking(
            service_id=service_id,
            student_id=student_id,
            scheduled_start_at=datetime.now(timezone.utc),
        )
    )
    await test_session.flush()

    test_session.add(
        ServiceBooking(
            service_id=service_id,
            student_id=student_id,
            scheduled_start_at=datetime.now(timezone.utc),
        )
    )
    with pytest.raises(IntegrityError):
        await test_session.flush()
