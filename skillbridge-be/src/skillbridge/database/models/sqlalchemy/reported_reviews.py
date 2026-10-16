from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class ReportedReview(BaseModel, BaseModelMixin):
    __tablename__ = "reported_reviews"
    __table_args__ = (
        CheckConstraint(
            "(tutor_review_id IS NOT NULL AND service_review_id IS NULL) OR "
            "(tutor_review_id IS NULL AND service_review_id IS NOT NULL)",
            name="ck_reported_reviews_exact_target",
        ),
        UniqueConstraint(
            "reporter_user_id",
            "tutor_review_id",
            name="uq_reported_tutor_review_reporter",
        ),
        UniqueConstraint(
            "reporter_user_id",
            "service_review_id",
            name="uq_reported_service_review_reporter",
        ),
        Index("ix_reported_reviews_reported_at", "reported_at"),
    )

    reporter_user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tutor_review_id = Column(
        UUIDType,
        ForeignKey("tutor_reviews.id", ondelete="CASCADE"),
        nullable=True,
    )
    service_review_id = Column(
        UUIDType,
        ForeignKey("service_reviews.id", ondelete="CASCADE"),
        nullable=True,
    )
    reason = Column(String(1024), nullable=False)
    reported_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reporter_user = relationship("User", foreign_keys=[reporter_user_id], lazy="noload")
    reported_tutor_review = relationship(
        "TutorReview",
        back_populates="tutor_review_reports",
        foreign_keys=[tutor_review_id],
        lazy="noload",
    )
    reported_service_review = relationship(
        "ServiceReview",
        back_populates="service_review_reports",
        foreign_keys=[service_review_id],
        lazy="noload",
    )
