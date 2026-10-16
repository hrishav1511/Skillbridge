from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional
from uuid import UUID

# ── Incoming WS payloads ──────────────────────────────────────────────────────


class SendMessagePayload(BaseModel):
    chat_room_id: UUID
    content: str = Field(min_length=1, max_length=4000)
    client_message_id: Optional[UUID] = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be blank.")
        return value


class FetchHistoryPayload(BaseModel):
    chat_room_id: UUID
    before_message_id: Optional[UUID] = None  # for pagination; None = latest
    limit: int = 30


class MarkReadPayload(BaseModel):
    chat_room_id: UUID
    message_id: UUID  # mark everything up to and including this id as read


class TypingPayload(BaseModel):
    chat_room_id: UUID
    is_typing: bool


# ── REST payloads ─────────────────────────────────────────────────────────────


class CreateDirectRoomRequest(BaseModel):
    target_user_id: UUID
    user_id: UUID | None = None


class CreateGroupRoomRequest(BaseModel):
    name: str
    member_ids: list[UUID]


class CheckDirectRoomResponse(BaseModel):
    room_exists: bool
    chat_room_id: UUID | None = None


# ── Outgoing shapes ───────────────────────────────────────────────────────────


class MessageOut(BaseModel):
    id: UUID
    chat_room_id: UUID
    sender_id: UUID
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
