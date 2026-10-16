import enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from .base import BaseModel, UUIDType


class RescheduleProposalStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class BookingRescheduleProposal(BaseModel):
    __tablename__ = "booking_reschedule_proposals"
    __table_args__ = (
        CheckConstraint(
            "proposal_status IN ('PENDING', 'ACCEPTED', 'REJECTED')",
            name="ck_booking_reschedule_proposal_status",
        ),
        Index("ix_booking_reschedule_booking_created", "booking_id", "created_at"),
        Index("ix_booking_reschedule_booking_status", "booking_id", "proposal_status"),
    )

    booking_id = Column(
        UUIDType,
        ForeignKey("service_bookings.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposed_by_user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_start_at = Column(DateTime(timezone=True), nullable=False)
    proposed_start_at = Column(DateTime(timezone=True), nullable=False)
    proposal_status = Column(
        String(20),
        nullable=False,
        default=RescheduleProposalStatus.PENDING.value,
    )
    responded_at = Column(DateTime(timezone=True), nullable=True)
    responded_by_user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    proposal_booking = relationship(
        "ServiceBooking",
        back_populates="booking_reschedule_proposals",
        foreign_keys=[booking_id],
        lazy="noload",
    )
    proposal_user = relationship("User", foreign_keys=[proposed_by_user_id], lazy="noload")
    responder_user = relationship("User", foreign_keys=[responded_by_user_id], lazy="noload")
