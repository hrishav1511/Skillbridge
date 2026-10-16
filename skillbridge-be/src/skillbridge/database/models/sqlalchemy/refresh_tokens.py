from .base import BaseModel, BaseModelMixin, UUIDType
from sqlalchemy import Column, DateTime, String, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship


class RefreshToken(BaseModel, BaseModelMixin):
    __tablename__ = "refresh_tokens"

    token = Column(String(500), unique=True, nullable=False)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True),server_default=func.now(), nullable=True)
    

    refresh_token_user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_refresh_token",
        lazy="noload",
    )