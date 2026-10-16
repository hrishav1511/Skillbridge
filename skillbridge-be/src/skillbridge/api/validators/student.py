from uuid import UUID

from pydantic import BaseModel

from skillbridge.utils.renderer import BaseQueryCriteria


class CreateStudentInputValidator(BaseModel):
    field_of_study: str | None = None
    enrolled_university: str | None = None
    graduation_year: int | None = None


class StudentSearchValidator(BaseQueryCriteria):
    student_id: UUID | None = None
    field_of_study: str | None = None
    enrolled_university: str | None = None
