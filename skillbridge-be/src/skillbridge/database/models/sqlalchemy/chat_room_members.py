from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class ChatRoomMember(BaseModel, BaseModelMixin):
    __tablename__ = "chat_room_members"

    chat_room_id = Column(
        UUIDType,
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    joined_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    crm_chat_room = relationship(
        "ChatRoom",
        foreign_keys=[chat_room_id],
        back_populates="chat_room_crm",
        lazy="noload",
    )

    crm_user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_crm",
        lazy="noload",
    )
