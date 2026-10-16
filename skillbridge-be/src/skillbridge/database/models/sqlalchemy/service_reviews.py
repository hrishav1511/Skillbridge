from sqlalchemy import Column, ForeignKey, String, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class ServiceReview(BaseModel, BaseModelMixin):
    __tablename__ = "service_reviews"
    __table_args__ = (
        UniqueConstraint("service_id", "student_id", name="uq_service_review_service_student"),
    )

    service_id = Column(
        UUIDType,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = Column(
        UUIDType,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating = Column(Float, nullable=False)
    comment = Column(String(1024), nullable=True)

    service_review_service = relationship(
        "Service",
        foreign_keys=[service_id],
        back_populates="service_service_review",
        lazy="noload",
    )

    service_review_student = relationship(
        "Student",
        foreign_keys=[student_id],
        back_populates="student_service_review",
        lazy="noload",
    )

    service_review_reports = relationship(
        "ReportedReview",
        back_populates="reported_service_review",
        cascade="all, delete-orphan",
        lazy="noload",
    )
