from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.filters.service_booking import ServiceBookingSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.repositories.user_role_association import (
    UserRoleAssociationRepository,
)
from skillbridge.api.validators.service import CreateServiceBookingInputValidator
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.booking_reschedule_proposals import (
    BookingRescheduleProposal,
    RescheduleProposalStatus,
)
from skillbridge.database.models.sqlalchemy.service_bookings import (
    BookingStatus,
    ServiceBooking,
    booking_transition_allowed,
)
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import BaseExceptionMixin
from skillbridge.utils.renderer import Status
from skillbridge.utils.service_time import service_datetime


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ServiceBookingRepository(BaseRepository):
    model = ServiceBooking
    search_filter = ServiceBookingSearchFilter

    async def _participant_user_ids(
        self,
        session: AsyncSession,
        booking: ServiceBooking,
        service: Service,
    ) -> tuple[UUID | None, UUID | None]:
        student_user_id = (
            await session.execute(
                select(UserRoleAssociation.user_id).where(
                    UserRoleAssociation.student_id == booking.student_id
                )
            )
        ).scalar_one_or_none()
        tutor_user_id = (
            await session.execute(
                select(UserRoleAssociation.user_id).where(
                    UserRoleAssociation.tutor_id == service.tutor_id
                )
            )
        ).scalar_one_or_none()
        return student_user_id, tutor_user_id

    async def _locked_booking(
        self, session: AsyncSession, booking_id: UUID
    ) -> tuple[ServiceBooking, Service]:
        row = (
            await session.execute(
                select(ServiceBooking, Service)
                .join(Service, Service.id == ServiceBooking.service_id)
                .where(ServiceBooking.id == booking_id)
                .with_for_update()
            )
        ).first()
        if row is None:
            raise BaseExceptionMixin("Booking not found.", status_code=404)
        return row

    async def _assert_participant(
        self,
        session: AsyncSession,
        booking: ServiceBooking,
        service: Service,
        user_id: UUID,
        *,
        allow_admin: bool = False,
    ) -> tuple[UUID | None, UUID | None]:
        participant_ids = await self._participant_user_ids(session, booking, service)
        if user_id in participant_ids:
            return participant_ids
        if allow_admin and await UserRoleAssociationRepository().is_user_admin(
            user_id=user_id, session=session
        ):
            return participant_ids
        raise BaseExceptionMixin("Booking access is forbidden.", status_code=403)

    @staticmethod
    def _transition(booking: ServiceBooking, target: BookingStatus) -> None:
        if not booking_transition_allowed(booking.status, target):
            raise BaseExceptionMixin(
                f"Booking cannot transition from {booking.status} to {target.value}.",
                status_code=409,
            )
        booking.status = target.value
        booking.status_updated_at = datetime.now(timezone.utc)

    async def _notify(
        self,
        session: AsyncSession,
        *,
        user_id: UUID | None,
        notification_type: str,
        title: str,
        message: str,
        data: dict,
    ):
        if user_id is None:
            return None
        return await NotificationRepository().create_for_user(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            session=session,
        )

    async def _deliver(self, notifications: list) -> None:
        for notification in notifications:
            if notification is not None:
                await NotificationRepository().deliver_live(notification)

    async def create_service_booking(
        self, service_booking_input: CreateServiceBookingInputValidator
    ):
        notifications = []
        async with get_session() as session:
            service_row = (
                await session.execute(
                    select(Service, Tutor, User)
                    .join(Tutor, Tutor.id == Service.tutor_id)
                    .join(
                        UserRoleAssociation,
                        UserRoleAssociation.tutor_id == Tutor.id,
                    )
                    .join(User, User.id == UserRoleAssociation.user_id)
                    .where(Service.id == service_booking_input.service_id)
                )
            ).first()
            if service_row is None:
                raise BaseExceptionMixin("Service not found.", status_code=404)
            service, tutor, tutor_user = service_row

            if (
                str(service.status).upper() != Status.ACTIVE.value
                or str(tutor.status).upper() != Status.ACTIVE.value
                or str(tutor_user.status).upper() != Status.ACTIVE.value
                or str(tutor.approval_status).upper() not in {"ACCEPTED", "APPROVED"}
                or not tutor.is_visible
                or not tutor.accepting_requests
            ):
                raise BaseExceptionMixin(
                    "This service is not currently available for requests.",
                    status_code=409,
                )

            scheduled_start_at = service_datetime(service.date, service.time)
            if scheduled_start_at <= datetime.now(timezone.utc):
                raise BaseExceptionMixin(
                    "This service is no longer bookable because its start time has passed.",
                    status_code=400,
                )

            existing_booking = (
                await session.execute(
                    select(ServiceBooking.id).where(
                        ServiceBooking.service_id == service.id,
                        ServiceBooking.student_id == service_booking_input.student_id,
                    )
                )
            ).scalar_one_or_none()
            if existing_booking is not None:
                raise BaseExceptionMixin(
                    "You already have a request for this service.", status_code=409
                )

            booking = ServiceBooking(
                service_id=service.id,
                student_id=service_booking_input.student_id,
                status=BookingStatus.PENDING.value,
                scheduled_start_at=scheduled_start_at,
                status_updated_at=datetime.now(timezone.utc),
            )
            session.add(booking)
            await session.flush()
            await session.refresh(booking)
            notifications.append(
                await self._notify(
                    session,
                    user_id=tutor_user.id,
                    notification_type="SESSION_REQUESTED",
                    title="New service request",
                    message=f"A student requested '{service.service_name}'.",
                    data={"booking_id": str(booking.id), "service_id": str(service.id)},
                )
            )
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise BaseExceptionMixin(
                    "You already have a request for this service.", status_code=409
                ) from exc

        await self._deliver(notifications)
        return {
            "success": True,
            "message": "Session request created.",
            "data": booking,
        }

    async def get_booking_for_user(self, booking_id: UUID, user_id: UUID):
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            await self._assert_participant(
                session, booking, service, user_id, allow_admin=True
            )
            return booking

    async def accept_booking(self, booking_id: UUID, tutor_user_id: UUID):
        notifications = []
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(
                tutor_user_id, session=session
            )
            if tutor_id is None or tutor_id != service.tutor_id:
                raise BaseExceptionMixin(
                    "Only the service tutor may accept this request.", status_code=403
                )
            self._transition(booking, BookingStatus.ACCEPTED)
            student_user_id, _ = await self._participant_user_ids(
                session, booking, service
            )
            notifications.append(
                await self._notify(
                    session,
                    user_id=student_user_id,
                    notification_type="SESSION_ACCEPTED",
                    title="Service request accepted",
                    message=f"Your request for '{service.service_name}' was accepted.",
                    data={"booking_id": str(booking.id), "service_id": str(service.id)},
                )
            )
            await session.commit()
        await self._deliver(notifications)
        return {
            "success": True,
            "message": "Session request accepted.",
            "data": booking,
        }

    async def decline_booking(self, booking_id: UUID, tutor_user_id: UUID):
        notifications = []
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(
                tutor_user_id, session=session
            )
            if tutor_id is None or tutor_id != service.tutor_id:
                raise BaseExceptionMixin(
                    "Only the service tutor may decline this request.", status_code=403
                )
            self._transition(booking, BookingStatus.DECLINED)
            student_user_id, _ = await self._participant_user_ids(
                session, booking, service
            )
            notifications.append(
                await self._notify(
                    session,
                    user_id=student_user_id,
                    notification_type="SESSION_DECLINED",
                    title="Service request declined",
                    message=f"Your request for '{service.service_name}' was declined.",
                    data={"booking_id": str(booking.id), "service_id": str(service.id)},
                )
            )
            await session.commit()
        await self._deliver(notifications)
        return {
            "success": True,
            "message": "Session request declined.",
            "data": booking,
        }

    async def cancel_service_booking(
        self,
        booking_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ):
        notifications = []
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            student_user_id, tutor_user_id = await self._assert_participant(
                session, booking, service, user_id, allow_admin=True
            )
            if _utc(booking.scheduled_start_at) <= datetime.now(timezone.utc):
                raise BaseExceptionMixin(
                    "A started or completed session cannot be cancelled.",
                    status_code=409,
                )
            self._transition(booking, BookingStatus.CANCELLED)
            booking.cancelled_at = datetime.now(timezone.utc)
            booking.cancelled_by_user_id = user_id
            booking.cancellation_reason = reason
            await session.execute(
                update(BookingRescheduleProposal)
                .where(
                    BookingRescheduleProposal.booking_id == booking.id,
                    BookingRescheduleProposal.proposal_status
                    == RescheduleProposalStatus.PENDING.value,
                )
                .values(
                    proposal_status=RescheduleProposalStatus.REJECTED.value,
                    responded_at=datetime.now(timezone.utc),
                    responded_by_user_id=user_id,
                )
            )
            if user_id == student_user_id:
                recipients = [tutor_user_id]
            elif user_id == tutor_user_id:
                recipients = [student_user_id]
            else:
                recipients = [student_user_id, tutor_user_id]
            for recipient in dict.fromkeys(recipients):
                notifications.append(
                    await self._notify(
                        session,
                        user_id=recipient,
                        notification_type="SESSION_CANCELLED",
                        title="Service cancelled",
                        message=f"The service for '{service.service_name}' was cancelled.",
                        data={
                            "booking_id": str(booking.id),
                            "service_id": str(service.id),
                        },
                    )
                )
            await session.commit()
        await self._deliver(notifications)
        return {
            "success": True,
            "message": "Session cancelled.",
            "data": {"booking_id": booking.id, "status": booking.status},
        }

    async def propose_reschedule(
        self, booking_id: UUID, user_id: UUID, proposed_start_at: datetime
    ):
        notifications = []
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            student_user_id, tutor_user_id = await self._assert_participant(
                session, booking, service, user_id
            )
            if booking.status != BookingStatus.ACCEPTED.value:
                raise BaseExceptionMixin(
                    "Only accepted services can be rescheduled.", status_code=409
                )
            proposed_start_at = _utc(proposed_start_at)
            if proposed_start_at <= datetime.now(timezone.utc):
                raise BaseExceptionMixin(
                    "The proposed time must be in the future.", status_code=422
                )
            pending = (
                await session.execute(
                    select(BookingRescheduleProposal.id).where(
                        BookingRescheduleProposal.booking_id == booking.id,
                        BookingRescheduleProposal.proposal_status
                        == RescheduleProposalStatus.PENDING.value,
                    )
                )
            ).scalar_one_or_none()
            if pending is not None:
                raise BaseExceptionMixin(
                    "This service already has a pending reschedule proposal.",
                    status_code=409,
                )
            proposal = BookingRescheduleProposal(
                booking_id=booking.id,
                proposed_by_user_id=user_id,
                previous_start_at=booking.scheduled_start_at,
                proposed_start_at=proposed_start_at,
                proposal_status=RescheduleProposalStatus.PENDING.value,
            )
            session.add(proposal)
            await session.flush()
            await session.refresh(proposal)
            recipient = tutor_user_id if user_id == student_user_id else student_user_id
            notifications.append(
                await self._notify(
                    session,
                    user_id=recipient,
                    notification_type="RESCHEDULE_PROPOSED",
                    title="New reschedule proposal",
                    message=f"A new time was proposed for '{service.service_name}'.",
                    data={
                        "booking_id": str(booking.id),
                        "proposal_id": str(proposal.id),
                        "proposed_start_at": proposed_start_at.isoformat(),
                    },
                )
            )
            await session.commit()
        await self._deliver(notifications)
        return proposal

    async def respond_to_reschedule(
        self,
        booking_id: UUID,
        proposal_id: UUID,
        user_id: UUID,
        *,
        accept: bool,
    ):
        notifications = []
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            await self._assert_participant(session, booking, service, user_id)
            proposal = (
                await session.execute(
                    select(BookingRescheduleProposal)
                    .where(
                        BookingRescheduleProposal.id == proposal_id,
                        BookingRescheduleProposal.booking_id == booking.id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if proposal is None:
                raise BaseExceptionMixin(
                    "Reschedule proposal not found.", status_code=404
                )
            if proposal.proposed_by_user_id == user_id:
                raise BaseExceptionMixin(
                    "The proposer cannot respond to their own proposal.",
                    status_code=403,
                )
            if proposal.proposal_status != RescheduleProposalStatus.PENDING.value:
                raise BaseExceptionMixin(
                    "This reschedule proposal has already been resolved.",
                    status_code=409,
                )
            if booking.status != BookingStatus.ACCEPTED.value:
                raise BaseExceptionMixin(
                    "This booking can no longer be rescheduled.", status_code=409
                )

            proposal.responded_at = datetime.now(timezone.utc)
            proposal.responded_by_user_id = user_id
            if accept:
                proposal.proposal_status = RescheduleProposalStatus.ACCEPTED.value
                booking.scheduled_start_at = proposal.proposed_start_at
                booking.status_updated_at = datetime.now(timezone.utc)
                notification_type = "RESCHEDULE_ACCEPTED"
                title = "Reschedule accepted"
                message = (
                    f"Your proposed time for '{service.service_name}' was accepted."
                )
            else:
                proposal.proposal_status = RescheduleProposalStatus.REJECTED.value
                notification_type = "RESCHEDULE_REJECTED"
                title = "Reschedule rejected"
                message = (
                    f"Your proposed time for '{service.service_name}' was rejected."
                )

            notifications.append(
                await self._notify(
                    session,
                    user_id=proposal.proposed_by_user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    data={
                        "booking_id": str(booking.id),
                        "proposal_id": str(proposal.id),
                    },
                )
            )
            await session.commit()
        await self._deliver(notifications)
        return proposal

    async def list_reschedule_history(self, booking_id: UUID, user_id: UUID):
        async with get_session() as session:
            booking, service = await self._locked_booking(session, booking_id)
            await self._assert_participant(
                session, booking, service, user_id, allow_admin=True
            )
            result = await session.execute(
                select(BookingRescheduleProposal)
                .where(BookingRescheduleProposal.booking_id == booking.id)
                .order_by(BookingRescheduleProposal.created_at.desc())
            )
            return list(result.scalars().all())
