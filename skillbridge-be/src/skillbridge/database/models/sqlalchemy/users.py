import enum

from sqlalchemy import Boolean, Column, String, TypeDecorator
from sqlalchemy.orm import declared_attr, relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class Gender(str, enum.Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"

    def __str__(self):
        return self.value


class PhoneType(str, enum.Enum):
    IOS = "IOS"
    ANDROID = "ANDROID"

    def __str__(self):
        return self.value


class HexByteString(TypeDecorator):
    """Convert Python bytestring to string with hexadecimal digits and back for storage."""

    impl = String(255)  # Fixed: added length
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if not isinstance(value, bytes):
            raise TypeError("HexByteString columns support only bytes values.")
        return value.hex()

    def process_result_value(self, value, dialect):
        return bytes.fromhex(value) if value else None


class User(BaseModel, BaseModelMixin):
    __tablename__ = "users"

    full_name = Column(String(255))
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255))
    phone = Column(String(50), nullable=True)
    auth_id = Column(String(255), nullable=True)
    has_registered = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    user_ura = relationship(
        "UserRoleAssociation",
        foreign_keys="[UserRoleAssociation.user_id]",
        cascade="delete, merge, save-update",
        back_populates="ura_user",
        lazy="noload",
    )

    user_tutor_revisions = relationship(
        "TutorRevision",
        foreign_keys="[TutorRevision.user_id]",
        back_populates="tutor_revision_user",
        lazy="noload",
    )

    user_crm = relationship(
        "ChatRoomMember",
        foreign_keys="[ChatRoomMember.user_id]",
        cascade="delete, merge, save-update",
        back_populates="crm_user",
        lazy="noload",
    )

    user_chat_message = relationship(
        "ChatMessage",
        foreign_keys="[ChatMessage.sender_id]",
        cascade="delete, merge, save-update",
        back_populates="chat_message_user",
        lazy="noload",
    )

    user_mrs = relationship(
        "MessageReadStatus",
        foreign_keys="[MessageReadStatus.user_id]",
        cascade="delete, merge, save-update",
        back_populates="mrs_user",
        lazy="noload",
    )

    user_refresh_token = relationship(
        "RefreshToken",
        foreign_keys="[RefreshToken.user_id]",
        cascade="delete, merge, save-update",
        back_populates="refresh_token_user",
        lazy="noload",
    )

    user_notifications = relationship(
        "Notification",
        foreign_keys="[Notification.user_id]",
        cascade="delete, merge, save-update",
        back_populates="notification_user",
        lazy="noload",
    )


    @declared_attr
    def created_by(cls):
        return relationship(
            "User",
            foreign_keys=[cls.created_by_id],
            backref="created_items",
            remote_side=[cls.id],  # Fixed: use list instead of string
        )

    @declared_attr
    def updated_by(cls):
        return relationship(
            "User",
            foreign_keys=[cls.updated_by_id],
            backref="updated_items",
            remote_side=[cls.id],  # Fixed: use list instead of string
        )
