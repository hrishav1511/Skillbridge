from sqlalchemy import Column, ForeignKey, String, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class TutorReview(BaseModel, BaseModelMixin):
    __tablename__ = "tutor_reviews"
    __table_args__ = (
        UniqueConstraint("tutor_id", "student_id", name="uq_tutor_review_tutor_student"),
    )

    tutor_id = Column(
        UUIDType,
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = Column(
        UUIDType,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating = Column(Float, nullable=False)
    comment = Column(String(1024), nullable=True)

    tutor_review_tutor = relationship(
        "Tutor",
        foreign_keys=[tutor_id],
        back_populates="tutor_tutor_review",
        lazy="noload",
    )

    tutor_review_student = relationship(
        "Student",
        foreign_keys=[student_id],
        back_populates='student_tutor_review',
        lazy="noload",
    )

    tutor_review_reports = relationship(
        "ReportedReview",
        back_populates="reported_tutor_review",
        cascade="all, delete-orphan",
        lazy="noload",
    )
