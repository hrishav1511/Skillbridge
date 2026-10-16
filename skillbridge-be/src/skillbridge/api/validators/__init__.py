from uuid import UUID

from pydantic import BaseModel

from skillbridge.utils.renderer import BaseQueryCriteria


class CreateTutorProfileInputValidator(BaseModel):
    title: str
    tutor_profile_id: UUID | None = None
    description: str | None = None


class TutorProfileSearchValidator(BaseQueryCriteria):
    tutor_profile_id: UUID | None = None
