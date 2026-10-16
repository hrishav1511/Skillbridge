from typing import List
from uuid import UUID

from pydantic import BaseModel
from datetime import date as DateType, datetime, time as TimeType

from skillbridge.api.schemas.user import UserOutput
from skillbridge.api.validators.service import RevisionType
from skillbridge.utils.renderer import (
    BaseInModel,
    BaseOutModel,
    BaseQueryCriteria,
    BaseResponse,
    Status,
)


class CreateTutorInput(BaseModel):
    user_id: UUID
    academic_program: str | None = None
    bio: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    is_visible: bool | None = None
    approval_status: str | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None


class CreateTutorOutput(BaseModel):
    id: UUID
    user_id: UUID | None = None
    academic_program: str | None = None
    bio: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    is_visible: bool | None = None
    approval_status: str | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None


class CreateTutorResponse(BaseResponse):
    data: CreateTutorOutput


class ProfilePictureUploadResponse(BaseResponse):
    profile_picture_url: str


class CoverPictureUploadResponse(BaseResponse):
    cover_picture_url: str


class TutorModel(BaseModel):
    academic_program: str | None = None
    bio: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    is_visible: bool | None = None
    approval_status: str | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None


class TutorOutput(BaseModel):
    id: UUID
    is_favorite: bool = False
    account_status: str | None = None
    academic_program: str | None = None
    bio: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    is_visible: bool | None = None
    approval_status: str | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None
    average_rating: str | None = None
    user: UserOutput | None = None
    profile_picture_url: str | None = None
    cover_picture_url: str | None = None


class TutorRevisionOutput(TutorOutput):
    tutor_id: UUID | None = None
    full_name: str | None = None
    revision_type: RevisionType | None = None
    rejection_reason: str | None = None
    moderation_status: str = "SKIPPED"
    moderation_flag: bool = False
    moderation_categories: dict | None = None
    moderation_scores: dict | None = None
    moderation_reason: str | None = None
    moderation_provider: str | None = None
    moderated_at: datetime | None = None


class TutorRevisionModel(TutorModel):
    tutor_id: UUID | None = None
    user_id: UUID | None = None
    full_name: str | None = None
    revision_type: RevisionType | None = None
    moderation_status: str = "SKIPPED"
    moderation_flag: bool = False
    moderation_categories: dict | None = None
    moderation_scores: dict | None = None
    moderation_reason: str | None = None
    moderation_provider: str | None = None
    moderated_at: datetime | None = None

class RejectTutorRevisionInput(BaseModel):
    rejection_reason: str


class UpdateTutorInput(BaseModel):
    full_name: str | None = None
    academic_program: str | None = None
    bio: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    is_visible: bool | None = None
    approval_status: Status | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None


class UpdateTutorOutput(BaseModel):
    id: UUID
    academic_program: str | None = None
    bio: str | None = None
    phone: str | None = None
    teaching_style: str | None = None
    is_visible: bool | None = None
    approval_status: str | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None
    user: UserOutput | None = None


class UpdateTutorResponse(BaseResponse):
    data: UpdateTutorOutput


class PaginatedTutors(BaseResponse):
    data: List[TutorOutput]


class TutorAccountStatusInput(BaseModel):
    status: str


class PaginatedTutorRevisions(BaseResponse):
    data: List[TutorRevisionOutput]


class CreateTutorRevisionResponse(BaseResponse):
    data: TutorRevisionOutput


class UpdateTutorRevisionResponse(BaseResponse):
    data: TutorRevisionOutput


class ApproveTutorRevisionResponse(BaseResponse):
    data: TutorRevisionOutput


class RejectTutorRevisionResponse(BaseResponse):
    data: TutorRevisionOutput


class ListTutorRevisionsResponse(BaseResponse):
    data: List[TutorRevisionOutput]


class TutorQueryCriteria(BaseQueryCriteria):
    tutor_id: UUID | None = None
    academic_program: str | None = None
    tag: str | None = None
    teaching_style: str | None = None
    # Optional explicit user name filter (searches associated user's full_name)
    full_name: str | None = None
    approval_status: Status = Status.ALL
    favorite_only: bool = False
    public_only: bool = False


class AcademicProgramListResponse(BaseResponse):
    """The distinct academic programs available to filter by."""

    data: List[str]


class TutorTagListResponse(BaseResponse):
    """The distinct subject tags available to filter by."""

    data: List[str]


class TutorVisibilityInput(BaseModel):
    is_visible: bool


class TutorAvailabilityInput(BaseModel):
    accepting_requests: bool


class TutorControlOutput(BaseModel):
    tutor_id: UUID
    is_visible: bool
    accepting_requests: bool
