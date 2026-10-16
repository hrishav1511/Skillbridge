from __future__ import annotations

from datetime import date as DateType, datetime, time as TimeType
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from skillbridge.api.schemas.user import UserOutput
from skillbridge.api.validators.service import (
    ServiceLevel,
    RevisionType,
    ServiceScheduleStatus,
)
from skillbridge.utils.renderer import BaseQueryCriteria, BaseResponse, Status


class CreateServiceInput(BaseModel):
    tutor_id: UUID
    service_name: str
    description: str | None = None
    date: Optional[DateType]
    time: Optional[TimeType]
    end_time: Optional[TimeType] = None
    price: int
    level: ServiceLevel
    joining_link: str | None = None
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_urls: list[str] | None = None
    tags: list[str] | None = None


class CreateServiceOutput(BaseModel):
    id: UUID
    tutor_id: UUID
    service_name: str
    description: str | None = None
    date: Optional[DateType]
    time: Optional[TimeType]
    end_time: Optional[TimeType] = None
    price: int
    level: ServiceLevel
    joining_link: str | None = None
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_urls: list[str] | None = None
    tags: list[str] | None = None
    approval_status: str | None = None
    rejection_reason: str | None = None


class CreateServiceBookingInput(BaseModel):
    service_id: UUID
    student_id: UUID | None = None


class CreateServiceBookingOutput(BaseModel):
    id: UUID
    service_id: UUID
    student_id: UUID
    status: str
    scheduled_start_at: datetime


class CreateServiceBookingResponse(BaseResponse):
    data: CreateServiceBookingOutput


class CreateServiceResponse(BaseResponse):
    data: CreateServiceOutput


class CreateServiceRevisionInput(CreateServiceInput):
    pass


class RejectServiceRevisionInput(BaseModel):
    rejection_reason: str


class ApproveServiceRevisionInput(BaseModel):
    override_moderation: bool = False


class UpdateServiceInput(BaseModel):
    service_name: str | None = None
    description: str | None = None
    date: Optional[DateType] = None
    time: Optional[TimeType] = None
    end_time: Optional[TimeType] = None
    price: int | None = None
    level: ServiceLevel | None = None
    joining_link: str | None = None
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_urls: list[str] | None = None
    tags: list[str] | None = None


class UpdateServiceOutput(BaseModel):
    id: UUID
    tutor_id: UUID
    service_name: str
    description: str | None = None
    date: Optional[DateType] = None
    time: Optional[TimeType] = None
    end_time: Optional[TimeType] = None
    price: int
    level: ServiceLevel
    joining_link: str | None = None
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_urls: list[str] | None = None
    tags: list[str] | None = None
    approval_status: str | None = None
    rejection_reason: str | None = None
    tutor: UserOutput | None = None


class UpdateServiceResponse(BaseResponse):
    data: UpdateServiceOutput


class ServiceOutput(BaseModel):
    id: UUID
    tutor_id: UUID
    service_name: str
    description: str | None = None
    date: Optional[DateType]
    time: Optional[TimeType]
    end_time: Optional[TimeType] = None
    schedule_status: ServiceScheduleStatus | None = None
    is_favorite: bool = False
    # Accepted bookings. The detail view derives its count the same way, so
    # both screens report the same number.
    enrolled_students_count: int = 0
    price: int
    level: ServiceLevel
    joining_link: str | None = None
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_urls: list[str] | None = None
    tags: list[str] | None = None
    average_rating: str | None = None
    approval_status: str | None = None
    rejection_reason: str | None = None
    # ``tutor_id`` is the tutors row; ``tutor`` is the *user account* behind
    # that tutor, so ``tutor.id`` is a user id. The two are different keys and
    # have been mistaken for one another, so the user id is also published
    # under an unambiguous name. Address a tutor with ``tutor_id`` and a person
    # (chat, reports) with ``tutor_user_id``.
    tutor: UserOutput | None = None
    tutor_user_id: UUID | None = None


class ServiceQueryCriteria(BaseQueryCriteria):
    service_id: UUID | None = None
    service_name: str | None = None
    tutor_name: str | None = None
    tutor_id: UUID | None = None
    schedule_status: ServiceScheduleStatus | None = None
    favorite_only: bool = False
    public_only: bool = False
    min_price: int | None = None
    max_price: int | None = None
    # Filters on the academic program of the tutor running the session.
    academic_program: str | None = None
    # approval_status: Status = Status.ACCEPTED


class ServiceModel(BaseModel):
    tutor_id: UUID
    service_name: str
    description: str | None = None
    date: Optional[DateType]
    time: Optional[TimeType]
    end_time: Optional[TimeType] = None
    price: int
    level: ServiceLevel
    joining_link: str | None = None
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_urls: list[str] | None = None
    tags: list[str] | None = None
    status: str | None = None


class ServiceRevisionOutput(ServiceOutput):
    service_id: UUID | None = None
    revision_type: RevisionType | None = None
    moderation_status: str = "SKIPPED"
    moderation_flag: bool = False
    moderation_categories: dict | None = None
    moderation_scores: dict | None = None
    moderation_reason: str | None = None
    moderation_provider: str | None = None
    moderated_at: datetime | None = None


class ServiceRevisionModel(ServiceModel):
    service_id: UUID | None = None
    revision_type: RevisionType | None = None
    moderation_status: str = "SKIPPED"
    moderation_flag: bool = False
    moderation_categories: dict | None = None
    moderation_scores: dict | None = None
    moderation_reason: str | None = None
    moderation_provider: str | None = None
    moderated_at: datetime | None = None


class ServiceBookingModel(BaseModel):
    service_id: UUID | None = None
    student_id: UUID | None = None
    status: str = "PENDING"
    scheduled_start_at: datetime



class CreateServiceRevisionResponse(BaseResponse):
    data: ServiceRevisionOutput


class UpdateServiceRevisionResponse(BaseResponse):
    data: ServiceRevisionOutput


class ApproveServiceRevisionResponse(BaseResponse):
    data: ServiceRevisionOutput


class RejectServiceRevisionResponse(BaseResponse):
    data: ServiceRevisionOutput


class ListServiceRevisionsResponse(BaseResponse):
    data: List[ServiceRevisionOutput]


class ServiceRevisionQueryCriteria(ServiceQueryCriteria):
    revision_id: UUID | None = None
    approval_status: Status = Status.ALL


class PaginatedServiceRevisions(BaseResponse):
    data: List[ServiceRevisionOutput]


class AdminServiceOutput(ServiceOutput):
    """A service as moderation sees it.

    ``status`` is deliberately not on the public ``ServiceOutput``: students
    only ever receive ACTIVE rows, so publishing the flag there would say
    nothing while widening the public contract.
    """

    status: str | None = None


class PaginatedAdminServices(BaseResponse):
    data: List[AdminServiceOutput]


class ServiceStatusInput(BaseModel):
    status: str


class PaginatedServices(BaseResponse):
    data: List[ServiceOutput]


class GetServiceOutput(ServiceOutput):
    pass


class GetServiceResponse(BaseResponse):
    data: GetServiceOutput


class DeleteServiceResponse(BaseResponse):
    data: ServiceOutput | None = None

