from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from skillbridge.database.models.sqlalchemy.base import BaseModel, BaseModelMixin, UUIDType


class ReportedTutor(BaseModel, BaseModelMixin):
    __tablename__ = "reported_tutors"

    student_id = Column(
        UUIDType,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    tutor_id = Column(
        UUIDType,
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason = Column(String(1024), nullable=False)
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reported_tutor_student = relationship(
        "Student",
        back_populates="student_reported_tutors",
        foreign_keys=[student_id],
        lazy="noload",
    )
    reported_tutor_tutor = relationship(
        "Tutor",
        back_populates="tutor_reported_tutors",
        foreign_keys=[tutor_id],
        lazy="noload",
    )
