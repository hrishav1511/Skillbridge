import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserDetail(BaseModel):
    id: int
    name: str | None
    status: str | None

    model_config = ConfigDict(from_attributes=True)


class ObjectDetail(BaseModel):
    id: int
    name: str | None
    slug: str | None
    status: str | None

    model_config = ConfigDict(from_attributes=True)


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TRASHED = "TRASHED"
    DELETED = "DELETED"
    ARCHIEVED = "ARCHIEVED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    INVALID = "INVALID"
    VALID = "VALID"
    VERIFIED = "VERIFIED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ANSWERED = "ANSWERED"
    CANCELLED = "CANCELLED"
    PAID = "PAID"
    RESOLVED = "RESOLVED"
    TIMED_OUT = "TIMED_OUT"
    ALL = "ALL"

    def __str__(self):
        return self.value


class EmergencyType(str, Enum):
    LOST_ITEM = "LOST_ITEM"
    MEDICAL = "MEDICAL"
    CRIME = "CRIME"
    LOST_FAMILY = "LOST_FAMILY"
    OTHER = "OTHER"

    def __str__(self):
        return self.value


class BaseResponse(BaseModel):
    success: bool = Field(default=False)
    message: str = Field(default="")
    metadata: dict = Field(default={})
    data: dict | list = Field(default={})

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class BaseInModel(BaseModel):
    # status: Status = Field(default=Status.INACTIVE)
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        use_enum_values=True,
    )


class BaseOutModel(BaseModel):
    id: int | str | UUID | None = None
    status: Status | None = None
    created_at: str | datetime.datetime | None = None
    updated_at: str | datetime.datetime | None = None
    deleted_at: str | datetime.datetime | None = None
    # created_by: UserDetail | None
    # updated_by: UserDetail | None


class BaseQueryCriteria(BaseModel):
    query: str | None = Field(
        default="",
        max_length=40,
        pattern=r"^[A-Za-z0-9@.\s-]*$",
        description="Search text may contain letters, numbers, spaces, @, period, and hyphen.",
    )
    start_date: datetime.date | None = Field(default=None)
    end_date: datetime.date | None = Field(default=None)
    page: int = Field(default=1, ge=1)
    items_per_page: int = Field(default=50, ge=1, le=100)
    sort: str = Field(default="created_at:desc")


class BaseSearchCriteria(BaseQueryCriteria):
    query: str | None
    status: list[Status] | None = Field(default=[Status.ACTIVE])
    ids: list[int] | None
    exclude_ids: list[int] | None
    # logged_in_user_id: int | None = Field(default=None, description="ID of logged in user")
    # user_ids: list[int] | None
    # excluded_user_ids: list[int] | None
    start_date: datetime.date | None
    end_date: datetime.date | None
    page: int = Field(default=1)
    items_per_page: int = Field(default=50)
    sort: str = Field(default="created_at:desc")

    # class Config:
    #     # json_encoders = {ObjectId: str}
    #     json_encoders = {UUid: str, Status: str}


class PaginationType(BaseModel):
    current_page: int
    total_page: int
    total_records: int
    items_per_page: int
