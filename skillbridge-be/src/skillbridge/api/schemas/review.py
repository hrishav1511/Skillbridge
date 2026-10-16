from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from skillbridge.utils.renderer import BaseQueryCriteria
from skillbridge.api.schemas.user import UserOutput


class CreateTutorReviewInput(BaseModel):
    tutor_id: UUID
    student_id: UUID
    rating: float = Field(ge=0, le=10)
    comment: str | None = None


class CreateServiceReviewInput(BaseModel):
    service_id: UUID
    student_id: UUID
    rating: float = Field(ge=0, le=10)
    comment: str | None = None


class TutorReviewOutput(BaseModel):
    id: UUID
    tutor_id: UUID
    student_id: UUID
    rating: float
    comment: str | None = None
    student: UserOutput | None = None
    created_at: datetime | None = None


class ServiceReviewOutput(BaseModel):
    id: UUID
    service_id: UUID
    student_id: UUID
    rating: float
    comment: str | None = None
    student: UserOutput | None = None
    created_at: datetime | None = None


class TutorReviewQueryCriteria(BaseQueryCriteria):
    tutor_id: UUID | None = None
    student_id: UUID | None = None


class ServiceReviewQueryCriteria(BaseQueryCriteria):
    service_id: UUID | None = None
    student_id: UUID | None = None
