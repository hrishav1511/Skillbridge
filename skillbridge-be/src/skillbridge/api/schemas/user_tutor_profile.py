from uuid import UUID

from pydantic import BaseModel


class UserTutorProfileAssociationModel(BaseModel):
    user_id: UUID
    tutor_profile_id: UUID
