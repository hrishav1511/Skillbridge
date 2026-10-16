import enum

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    TypeDecorator,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declared_attr, relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class Student(BaseModel, BaseModelMixin):
    __tablename__ = "students"

    field_of_study = Column(String(255))
    enrolled_university = Column(String(255))
    graduation_year = Column(Integer)
    profile_picture_url = Column(String(255), nullable=True)

    student_ura = relationship(
        "UserRoleAssociation",
        back_populates="ura_student",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    student_service_booking = relationship(
        "ServiceBooking",
        back_populates="service_booking_student",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

    student_tutor_review = relationship(
        "TutorReview",
        cascade="delete, merge, save-update",
        back_populates="tutor_review_student",
        lazy="noload",
    )

    student_service_review = relationship(
        "ServiceReview",
        cascade="delete, merge, save-update",
        back_populates="service_review_student",
        lazy="noload",
    )

    student_favorite_tutors = relationship(
        "StudentFavoriteTutor",
        back_populates="favorite_tutor_student",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    student_favorite_services = relationship(
        "StudentFavoriteService",
        back_populates="favorite_service_student",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    student_reported_tutors = relationship(
        "ReportedTutor",
        back_populates="reported_tutor_student",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    student_reported_services = relationship(
        "ReportedService",
        back_populates="reported_service_student",
        cascade="all, delete-orphan",
        lazy="noload",
    )