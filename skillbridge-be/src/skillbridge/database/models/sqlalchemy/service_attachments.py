from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class ServiceAttachment(BaseModel, BaseModelMixin):
    __tablename__ = "service_attachments"

    service_id = Column(
        UUIDType,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tutor_id = Column(
        UUIDType,
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    object_key = Column(String(512), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)

    attachment_service = relationship(
        "Service",
        back_populates="service_attachments",
        lazy="noload",
    )
    attachment_tutor = relationship(
        "Tutor",
        back_populates="tutor_service_attachments",
        lazy="noload",
    )