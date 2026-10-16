import enum

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, JSON, String, Time
from sqlalchemy.orm import relationship

from skillbridge.utils.renderer import Status

from .base import BaseModel, BaseModelMixin, UUIDType


class ServiceLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

    def __str__(self):
        return self.value


class Service(BaseModel, BaseModelMixin):
    __tablename__ = "services"

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
    tags = Column(JSON, default=list)

    service_tutor = relationship(
        "Tutor",
        foreign_keys=[tutor_id],
        back_populates="tutor_service",
        lazy="noload",
    )

    service_service_revision = relationship(
        "ServiceRevision",
        back_populates="service_revision_service",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    service_service_booking = relationship(
        "ServiceBooking",
        back_populates="service_booking_service",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    service_service_review = relationship(
        "ServiceReview",
        back_populates="service_review_service",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    service_attachments = relationship(
        "ServiceAttachment",
        back_populates="attachment_service",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    service_favorite_services = relationship(
        "StudentFavoriteService",
        back_populates="favorite_service_service",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    service_reported_services = relationship(
        "ReportedService",
        back_populates="reported_service_service",
        cascade="all, delete-orphan",
        lazy="noload",
    )

