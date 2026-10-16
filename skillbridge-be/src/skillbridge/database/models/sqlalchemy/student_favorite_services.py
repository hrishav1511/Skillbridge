from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class StudentFavoriteService(BaseModel, BaseModelMixin):
    __tablename__ = "student_favorite_services"
    __table_args__ = (
        UniqueConstraint("student_id", "service_id", name="uq_student_favorite_service"),
    )

    student_id = Column(UUIDType, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(UUIDType, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)

    favorite_service_student = relationship(
        "Student",
        back_populates="student_favorite_services",
        foreign_keys=[student_id],
        lazy="noload",
    )
    favorite_service_service = relationship(
        "Service",
        back_populates="service_favorite_services",
        foreign_keys=[service_id],
        lazy="noload",
    )