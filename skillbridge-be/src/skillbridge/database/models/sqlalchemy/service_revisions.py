from datetime import date as DateType, time as TimeType

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Time
from sqlalchemy.orm import relationship

from skillbridge.api.validators.service import RevisionType, ServiceLevel
from skillbridge.database.models.sqlalchemy.base import BaseModel, BaseModelMixin, UUIDType
from skillbridge.utils.renderer import Status


class ServiceRevision(BaseModel, BaseModelMixin):
    __tablename__ = "service_revisions"

    service_id = Column(
        UUIDType,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
    )
    tutor_id = Column(
        UUIDType,
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    price = Column(Integer, default=0)
    level = Column(
        Enum(ServiceLevel, name="service_level"),
        nullable=False,
        default=ServiceLevel.BEGINNER,
    )
    joining_link = Column(String(255), nullable=True)
    image_urls = Column(JSON, nullable=True)
    video_url = Column(String(512), nullable=True)
    video_urls = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    approval_status = Column(String(50), default=Status.PENDING)
    rejection_reason = Column(String(512), nullable=True)
    revision_type = Column(String(50), nullable=False, server_default=RevisionType.CREATE) 
    moderation_status = Column(String(50), nullable=False, server_default="SKIPPED")
    moderation_flag = Column(Boolean, nullable=False, server_default="0")
    moderation_categories = Column(JSON, nullable=True)
    moderation_scores = Column(JSON, nullable=True)
    moderation_reason = Column(String(1024), nullable=True)
    moderation_provider = Column(String(100), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)

    service_revision_service = relationship(
        "Service",
        back_populates="service_service_revision",
        lazy="noload",
    )
    service_revision_tutor = relationship(
        "Tutor",
        back_populates="tutor_service_revision",
        lazy="noload",
    )
