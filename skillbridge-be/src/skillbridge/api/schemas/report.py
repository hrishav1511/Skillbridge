from uuid import UUID

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from skillbridge.utils.renderer import BaseResponse


class CreateTutorReportInput(BaseModel):
    tutor_id: UUID
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("reason must contain at least 10 non-whitespace characters")
        return value


class CreateServiceReportInput(BaseModel):
    service_id: UUID
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("reason must contain at least 10 non-whitespace characters")
        return value


class CreateReviewReportInput(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("reason must contain at least 10 non-whitespace characters")
        return value


class ReportedTutorOutput(BaseModel):
    id: UUID
    student_id: UUID
    tutor_id: UUID
    reason: str
    # Resolved server-side so the admin panel can show who reported whom
    # without a lookup per row.
    reporter_name: str | None = None
    tutor_name: str | None = None
    tutor_profile_picture_url: str | None = None
    reported_at: datetime | None = None

    @field_validator("reported_at")
    @classmethod
    def stored_timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        # Stored naive by MySQL; label it UTC so clients do not read it as local.
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)



class ReportedServiceOutput(BaseModel):
    id: UUID
    student_id: UUID
    service_id: UUID
    reason: str
    reporter_name: str | None = None
    service_name: str | None = None
    reported_at: datetime | None = None

    @field_validator("reported_at")
    @classmethod
    def stored_timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        # Stored naive by MySQL; label it UTC so clients do not read it as local.
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)



class ReportedReviewOutput(BaseModel):
    id: UUID
    reporter_user_id: UUID
    review_type: Literal["tutor", "service"]
    review_id: UUID
    reason: str
    review_comment: str | None = None
    review_rating: float
    reporter_name: str | None = None
    reviewed_entity_name: str | None = None
    reported_at: datetime | None = None

    @field_validator("reported_at")
    @classmethod
    def stored_timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        # Stored naive by MySQL; label it UTC so clients do not read it as local.
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)



class TutorReportListResponse(BaseResponse):
    data: list[ReportedTutorOutput]


class ServiceReportListResponse(BaseResponse):
    data: list[ReportedServiceOutput]


class ReviewReportListResponse(BaseResponse):
    data: list[ReportedReviewOutput]


class TutorReportCreateResponse(BaseResponse):
    data: ReportedTutorOutput


class ServiceReportCreateResponse(BaseResponse):
    data: ReportedServiceOutput


class ReviewReportCreateResponse(BaseResponse):
    data: ReportedReviewOutput
