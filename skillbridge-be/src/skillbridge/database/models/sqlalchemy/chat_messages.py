from sqlalchemy import Column, ForeignKey, Text, Boolean, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class ChatMessage(BaseModel, BaseModelMixin):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "sender_id",
            "client_message_id",
            name="uq_chat_message_sender_client_id",
        ),
    )

    chat_room_id = Column(
        UUIDType,
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_id = Column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    content = Column(Text, nullable=False)
    client_message_id = Column(UUIDType, nullable=True, index=True)

    is_deleted = Column(Boolean, default=False, nullable=False)

    # `created_at` is provided by `BaseModel`; no need to redeclare it here.

    chat_message_chat_room = relationship(
        "ChatRoom",
        back_populates="chat_room_chat_message",
        lazy="noload",
    )

    chat_message_user = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="user_chat_message",
        lazy="noload",
    )

    chat_message_message_read_status = relationship(
        "MessageReadStatus",
        back_populates="message_read_status_chat_message",
        cascade="delete, merge, save-update",
        lazy="noload",
    )
