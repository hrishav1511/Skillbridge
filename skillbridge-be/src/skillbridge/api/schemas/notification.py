from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skillbridge.utils.renderer import BaseResponse


class NotificationOutput(BaseModel):
    id: UUID
    user_id: UUID
    notification_type: str
    title: str
    message: str
    data: dict | None = None
    is_read: bool
    is_delivered: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseResponse):
    data: list[NotificationOutput]


class NotificationResponse(BaseResponse):
    data: NotificationOutput
