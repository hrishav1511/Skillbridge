from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skillbridge.utils.renderer import BaseResponse


class ServiceAttachmentOutput(BaseModel):
    id: UUID
    service_id: UUID
    tutor_id: UUID
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime | None = None
    download_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceAttachmentListResponse(BaseResponse):
    data: list[ServiceAttachmentOutput]


class ServiceAttachmentResponse(BaseResponse):
    data: ServiceAttachmentOutput


class ServiceAttachmentDeleteOutput(BaseModel):
    id: UUID
    deleted: bool


class ServiceAttachmentDeleteResponse(BaseResponse):
    data: ServiceAttachmentDeleteOutput
