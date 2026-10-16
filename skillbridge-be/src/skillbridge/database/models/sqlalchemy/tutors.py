import enum

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    TypeDecorator,
    ForeignKey,
    Index,
    JSON,
    Text,
)
from sqlalchemy.orm import declared_attr, relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class Tutor(BaseModel, BaseModelMixin):
    __tablename__ = "tutors"

    academic_program = Column(String(255))
    bio = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    teaching_style = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=False)
    approval_status = Column(String(50), default="PENDING", nullable=False)
    accepting_requests = Column(Boolean, default=True)
    profile_picture_url = Column(String(255), nullable=True)
    cover_picture_url = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)

    tutor_ura = relationship(
        "UserRoleAssociation",
        back_populates="ura_tutor",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    tutor_service = relationship(
        "Service",
        back_populates="service_tutor",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    tutor_service_revision = relationship(
        "ServiceRevision",
        back_populates="service_revision_tutor",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    tutor_revision = relationship(
        "TutorRevision",
        back_populates="tutor_revision_tutor",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    tutor_tutor_review = relationship(
        "TutorReview",
        back_populates="tutor_review_tutor",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    tutor_service_attachments = relationship(
        "ServiceAttachment",
        back_populates="attachment_tutor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    tutor_favorite_tutors = relationship(
        "StudentFavoriteTutor",
        back_populates="favorite_tutor_tutor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    tutor_reported_tutors = relationship(
        "ReportedTutor",
        back_populates="reported_tutor_tutor",
        cascade="all, delete-orphan",
        lazy="noload",
    )
