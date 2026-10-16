from __future__ import annotations

import enum
from datetime import date as DateType, time as TimeType
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from urllib.parse import urlparse
from skillbridge.utils.renderer import BaseQueryCriteria, Status


class ServiceLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

    def __str__(self):
        return self.value


class RevisionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    def __str__(self):
        return self.value


class ServiceScheduleStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"

    def __str__(self):
        return self.value


class CreateServiceInputValidator(BaseModel):
    tutor_id: UUID
    service_name: str = Field(min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    date: DateType
    time: TimeType
    end_time: TimeType
    price: int = Field(ge=0, le=10000)
    level: ServiceLevel
    joining_link: Optional[str] = None
    image_urls: list[str] | None = None
    video_url: Optional[str] = None
    video_urls: list[str] | None = None
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("joining_link")
    @classmethod
    def validate_joining_link(cls, value):
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("joining_link must be a valid HTTP(S) URL")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value):
        if value and any(not tag.strip() or len(tag.strip()) > 40 for tag in value):
            raise ValueError("Each tag must contain 1 to 40 characters")
        return [tag.strip() for tag in value] if value else value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.date < DateType.today():
            raise ValueError("date cannot be in the past")
        if self.end_time <= self.time:
            raise ValueError("end_time must be later than time")
        return self


class CreateServiceBookingInputValidator(BaseModel):
    service_id: UUID
    student_id: UUID


class UpdateServiceInputValidator(BaseModel):
    service_name: Optional[str] = Field(default=None, min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    date: Optional[DateType] = None
    time: Optional[TimeType] = None
    end_time: Optional[TimeType] = None
    price: Optional[int] = Field(default=None, ge=0, le=10000)
    level: Optional[ServiceLevel] = None
    joining_link: Optional[str] = None
    image_urls: list[str] | None = None
    video_url: Optional[str] = None
    video_urls: list[str] | None = None
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("joining_link")
    @classmethod
    def validate_joining_link(cls, value):
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("joining_link must be a valid HTTP(S) URL")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value):
        if value and any(not tag.strip() or len(tag.strip()) > 40 for tag in value):
            raise ValueError("Each tag must contain 1 to 40 characters")
        return [tag.strip() for tag in value] if value else value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.date is not None and self.date < DateType.today():
            raise ValueError("date cannot be in the past")
        if self.time is not None and self.end_time is not None and self.end_time <= self.time:
            raise ValueError("end_time must be later than time")
        return self

class ServiceSearchValidator(BaseQueryCriteria):
    service_id: Optional[UUID] = None
    service_name: Optional[str] = None
    tutor_name: Optional[str] = None
    tutor_id: Optional[UUID] = None
    schedule_status: ServiceScheduleStatus | None = None
    public_only: bool = False
    min_price: int | None = None
    max_price: int | None = None
    # Sessions have no academic program of their own; this matches on the
    # program of the tutor running the session.
    academic_program: Optional[str] = None
    # approval_status: Optional[Status] = None


class ServiceBookingSearchValidator(BaseQueryCriteria):
    service_id: Optional[UUID] = None
    service_booking_id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    tutor_id: Optional[UUID] = None
    status: Optional[str] = None
