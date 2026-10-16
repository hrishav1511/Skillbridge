from sqlalchemy import Boolean, Column, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel, UUIDType


class Notification(BaseModel):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_user_delivered", "user_id", "is_delivered"),
    )

    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    is_delivered = Column(Boolean, nullable=False, default=False)

    notification_user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_notifications",
        lazy="noload",
    )
