from sqlalchemy import Boolean, Column, Enum, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from skillbridge.api.validators.service import RevisionType
from skillbridge.database.models.sqlalchemy.base import BaseModel, BaseModelMixin, UUIDType
from skillbridge.utils.renderer import Status


class TutorRevision(BaseModel, BaseModelMixin):
    __tablename__ = "tutor_revisions"

    tutor_id = Column(
        UUIDType,
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=True,
    )
    full_name = Column(String(255), nullable=True)
    academic_program = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    teaching_style = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=False)
    approval_status = Column(String(50), default=Status.PENDING)
    accepting_requests = Column(Boolean, default=True)
    tags = Column(JSON, nullable=True)
    rejection_reason = Column(String(512), nullable=True)
    revision_type = Column(String(50), nullable=False, server_default=RevisionType.CREATE)
    moderation_status = Column(String(50), nullable=False, server_default="SKIPPED")
    moderation_flag = Column(Boolean, nullable=False, server_default="0")
    moderation_categories = Column(JSON, nullable=True)
    moderation_scores = Column(JSON, nullable=True)
    moderation_reason = Column(String(1024), nullable=True)
    moderation_provider = Column(String(100), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    tutor_revision_tutor = relationship(
        "Tutor",
        back_populates="tutor_revision",
        lazy="noload",
    )

    tutor_revision_user = relationship(
        "User",
        back_populates="user_tutor_revisions",
        foreign_keys=[user_id],
        lazy="noload",
    )
