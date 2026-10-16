from uuid import UUID

from pydantic import BaseModel


class UserRoleAssociationModel(BaseModel):
    user_id: UUID
    role_id: UUID
    tutor_id: UUID | None = None
    student_id: UUID | None = None
