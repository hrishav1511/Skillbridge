from datetime import datetime, timezone
from typing import List
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

from skillbridge.config import settings
from skillbridge.api.schemas.service import ServiceOutput
from skillbridge.api.schemas.student import StudentOutput
from skillbridge.api.schemas.tutor import TutorOutput
from skillbridge.database.models.sqlalchemy.booking_reschedule_proposals import (
    RescheduleProposalStatus,
)
from skillbridge.database.models.sqlalchemy.service_bookings import BookingStatus
from skillbridge.utils.renderer import BaseQueryCriteria, BaseResponse


class ServiceBookingQueryCriteria(BaseQueryCriteria):
    service_id: UUID | None = None
    service_booking_id: UUID | None = None
    student_id: UUID | None = None
    tutor_id: UUID | None = None
    # Lets the attendance view ask for accepted bookings only, rather than
    # pulling every request and filtering in the browser.
    status: BookingStatus | None = None


class ServiceBookingOutput(BaseModel):
    id: UUID
    service_id: UUID | None = None
    student_id: UUID | None = None
    status: BookingStatus
    booking_status: BookingStatus | None = None
    scheduled_start_at: datetime
    status_updated_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    service: ServiceOutput | None = None
    student: StudentOutput | None = None
    tutor: TutorOutput | None = None
    reschedule_proposals: list["RescheduleProposalOutput"] = Field(default_factory=list)

    @field_validator(
        "scheduled_start_at", "status_updated_at", "cancelled_at", mode="before"
    )
    @classmethod
    def stored_timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class CancelBookingInput(BaseModel):
    reason: str | None = Field(default=None, max_length=512)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class RescheduleProposalInput(BaseModel):
    proposed_start_at: datetime

    @field_validator("proposed_start_at")
    @classmethod
    def validate_future_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo(settings.SERVICE_TIMEZONE))
        value = value.astimezone(timezone.utc)
        if value <= datetime.now(timezone.utc):
            raise ValueError("proposed_start_at must be in the future")
        return value


class RescheduleProposalOutput(BaseModel):
    id: UUID
    booking_id: UUID
    proposed_by_user_id: UUID
    previous_start_at: datetime
    proposed_start_at: datetime
    proposal_status: RescheduleProposalStatus
    created_at: datetime | None = None
    responded_at: datetime | None = None
    responded_by_user_id: UUID | None = None

    @field_validator(
        "previous_start_at",
        "proposed_start_at",
        "created_at",
        "responded_at",
        mode="before",
    )
    @classmethod
    def stored_timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class RescheduleHistoryResponse(BaseResponse):
    data: list[RescheduleProposalOutput]


class PaginatedServiceBookings(BaseResponse):
    data: List[ServiceBookingOutput]
