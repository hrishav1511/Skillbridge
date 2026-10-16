import enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .base import BaseModel, BaseModelMixin, UUIDType


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


ALLOWED_BOOKING_TRANSITIONS = {
    BookingStatus.PENDING: {
        BookingStatus.ACCEPTED,
        BookingStatus.DECLINED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.ACCEPTED: {BookingStatus.CANCELLED},
    BookingStatus.DECLINED: set(),
    BookingStatus.CANCELLED: set(),
}


def booking_transition_allowed(current: str, target: BookingStatus) -> bool:
    try:
        current_status = BookingStatus(str(current).upper())
    except ValueError:
        return False
    return target in ALLOWED_BOOKING_TRANSITIONS[current_status]


class ServiceBooking(BaseModel, BaseModelMixin):
    __tablename__ = "service_bookings"
    __table_args__ = (
        UniqueConstraint("service_id", "student_id", name="uq_service_booking_service_student"),
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED')",
            name="ck_service_bookings_status",
        ),
        Index("ix_service_bookings_status", "status"),
        Index("ix_service_bookings_scheduled_start", "scheduled_start_at"),
    )

    status = Column(String(20), nullable=False, default=BookingStatus.PENDING.value)

    service_id = Column(UUIDType, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUIDType, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    scheduled_start_at = Column(DateTime(timezone=True), nullable=False)
    status_updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancellation_reason = Column(String(512), nullable=True)

    service_booking_service = relationship(
        "Service",
        back_populates="service_service_booking",
        foreign_keys=[service_id],
        lazy="noload",
    )

    service_booking_student = relationship(
        "Student",
        back_populates="student_service_booking",
        foreign_keys=[student_id],
        lazy="noload",
    )

    booking_reschedule_proposals = relationship(
        "BookingRescheduleProposal",
        back_populates="proposal_booking",
        cascade="all, delete-orphan",
        lazy="noload",
    )
