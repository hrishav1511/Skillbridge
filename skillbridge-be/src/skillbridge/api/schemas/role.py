from typing import List, Optional
from uuid import UUID

from skillbridge.database.models.sqlalchemy.roles import ROLE_ENUM
from skillbridge.utils.renderer import (
    BaseInModel,
    BaseOutModel,
    BaseQueryCriteria,
    BaseResponse,
    Status,
)


class CreateRoleInput(BaseInModel):
    title: ROLE_ENUM
    status: Optional[Status] = None
    slug: str
    description: str | None = None


class CreateRoleOutput(BaseOutModel):
    title: ROLE_ENUM
    slug: str
    description: str | None = None


class CreateRoleResponse(BaseResponse):
    data: CreateRoleOutput


class PaginatedRoles(BaseResponse):
    data: List[dict]


class RoleQueryCriteria(BaseQueryCriteria):
    role_id: Optional[UUID] = None
