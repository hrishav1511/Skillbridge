from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class StudentFavoriteTutor(BaseModel, BaseModelMixin):
    __tablename__ = "student_favorite_tutors"
    __table_args__ = (
        UniqueConstraint("student_id", "tutor_id", name="uq_student_favorite_tutor"),
    )

    student_id = Column(UUIDType, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    tutor_id = Column(UUIDType, ForeignKey("tutors.id", ondelete="CASCADE"), nullable=False)

    favorite_tutor_student = relationship(
        "Student",
        back_populates="student_favorite_tutors",
        foreign_keys=[student_id],
        lazy="noload",
    )
    favorite_tutor_tutor = relationship(
        "Tutor",
        back_populates="tutor_favorite_tutors",
        foreign_keys=[tutor_id],
        lazy="noload",
    )