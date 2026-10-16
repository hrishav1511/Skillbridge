from typing import List
from uuid import UUID

from pydantic import BaseModel

from skillbridge.api.schemas.user import UserOutput
from skillbridge.utils.renderer import (
    BaseInModel,
    BaseOutModel,
    BaseQueryCriteria,
    BaseResponse,
    Status,
)


class CreateStudentInput(BaseModel):
    field_of_study: str | None = None
    enrolled_university: str | None = None
    graduation_year: int | None = None


class CreateStudentOutput(BaseModel):
    id: UUID
    field_of_study: str | None = None
    enrolled_university: str | None = None
    graduation_year: int | None = None


class CreateStudentResponse(BaseResponse):
    data: CreateStudentOutput


class StudentModel(BaseModel):
    field_of_study: str | None = None
    enrolled_university: str | None = None
    graduation_year: int | None = None
    profile_picture_url: str | None = None


class StudentOutput(BaseModel):
    id: UUID
    field_of_study: str | None = None
    enrolled_university: str | None = None
    graduation_year: int | None = None
    profile_picture_url: str | None = None
    user: UserOutput | None = None


class ProfilePictureUploadResponse(BaseResponse):
    profile_picture_url: str


class PaginatedStudents(BaseResponse):
    data: List[StudentOutput]


class StudentQueryCriteria(BaseQueryCriteria):
    student_id: UUID | None = None
    field_of_study: str | None = None
    enrolled_university: str | None = None
