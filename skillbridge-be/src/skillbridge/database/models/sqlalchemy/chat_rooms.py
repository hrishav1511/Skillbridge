from sqlalchemy import Column, String, Enum
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin


class ChatRoom(BaseModel, BaseModelMixin):
    __tablename__ = "chat_rooms"

    name = Column(String(255), nullable=True)
    room_type = Column(Enum("DIRECT", "GROUP"), nullable=False)

    chat_room_crm = relationship(
        "ChatRoomMember",
        back_populates="crm_chat_room",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    chat_room_chat_message = relationship(
        "ChatMessage",
        back_populates="chat_message_chat_room",
        cascade="delete, merge, save-update",
        lazy="noload",
    )
