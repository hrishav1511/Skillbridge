from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class MessageReadStatus(BaseModel, BaseModelMixin):
    __tablename__ = "message_read_status"

    chat_message_id = Column(
        UUIDType,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    read_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    message_read_status_chat_message = relationship(
        "ChatMessage",
        foreign_keys=[chat_message_id],
        back_populates="chat_message_message_read_status",
        lazy="noload",
    )

    mrs_user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_mrs",
        lazy="noload",
    )
