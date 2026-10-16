from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from skillbridge.database.models.sqlalchemy.base import BaseModel, BaseModelMixin, UUIDType


class ReportedService(BaseModel, BaseModelMixin):
    __tablename__ = "reported_services"

    student_id = Column(
        UUIDType,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id = Column(
        UUIDType,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason = Column(String(1024), nullable=False)
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reported_service_student = relationship(
        "Student",
        back_populates="student_reported_services",
        foreign_keys=[student_id],
        lazy="noload",
    )
    reported_service_service = relationship(
        "Service",
        back_populates="service_reported_services",
        foreign_keys=[service_id],
        lazy="noload",
    )
