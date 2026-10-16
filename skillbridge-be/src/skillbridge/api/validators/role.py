from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from skillbridge.database.models.sqlalchemy.roles import ROLE_ENUM
from skillbridge.utils.renderer import BaseQueryCriteria, Status


class CreateRoleInputValidator(BaseModel):
    title: ROLE_ENUM
    status: Optional[Status] = Status.ACTIVE
    slug: str
    description: str | None = None


class RoleSearchValidator(BaseQueryCriteria):
    role_id: Optional[UUID] = None
