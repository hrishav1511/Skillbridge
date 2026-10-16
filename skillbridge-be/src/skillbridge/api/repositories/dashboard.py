from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.schemas.dashboard import (
    StudentDashboardData,
    TutorDashboardCards,
    TutorDashboardData,
    TutorDashboardPerformance,
    UpcomingService,
    AdminDashboardData,
    MonthlyServicesDone,
)
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_bookings import (
    BookingStatus,
    ServiceBooking,
)
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.tutor_revisions import TutorRevision
from skillbridge.database.models.sqlalchemy.service_revisions import ServiceRevision
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.utils.renderer import Status
from skillbridge.utils.service_time import service_datetime
from skillbridge.config import settings


def _service_starts_at(service: Service) -> datetime:
    return datetime.combine(service.date, service.time)


def _is_upcoming(service: Service, now: datetime) -> bool:
    return _service_starts_at(service) > now.replace(tzinfo=None)


class DashboardRepository:
    async def get_admin_dashboard(self) -> AdminDashboardData:
        async with get_session() as session:
            total_students = (
                await session.execute(
                    select(func.count(func.distinct(UserRoleAssociation.student_id)))
                    .join(Role, UserRoleAssociation.role_id == Role.id)
                    .where(
                        UserRoleAssociation.student_id.is_not(None),
                        func.lower(Role.slug) == "student",
                    )
                )
            ).scalar_one()
            total_tutors = (
                await session.execute(select(func.count(Tutor.id)))
            ).scalar_one()
            total_services = (
                await session.execute(select(func.count(Service.id)))
            ).scalar_one()
            pending_services = (
                await session.execute(
                    select(func.count(ServiceRevision.id)).where(
                        ServiceRevision.approval_status == Status.PENDING
                    )
                )
            ).scalar_one()
            pending_tutors = (
                await session.execute(
                    select(func.count(TutorRevision.id)).where(
                        TutorRevision.approval_status == Status.PENDING
                    )
                )
            ).scalar_one()

            now = datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE))
            month_starts = []
            year = now.year
            month = now.month
            for _ in range(12):
                month_starts.append(date(year, month, 1))
                month -= 1
                if month == 0:
                    year -= 1
                    month = 12
            month_starts.reverse()
            month_keys = [item.strftime("%Y-%m") for item in month_starts]

            services = (
                await session.execute(
                    select(Service.date, Service.time, Service.end_time)
                )
            ).all()
            completed_by_month = Counter()
            current_utc = datetime.now(ZoneInfo("UTC"))
            for service in services:
                end_time = service.end_time or service.time
                if service_datetime(service.date, end_time) <= current_utc:
                    key = service.date.strftime("%Y-%m")
                    if key in month_keys:
                        completed_by_month[key] += 1

            return AdminDashboardData(
                total_students=int(total_students or 0),
                total_tutors=int(total_tutors or 0),
                total_services=int(total_services or 0),
                pending_items=int(pending_services or 0) + int(pending_tutors or 0),
                monthly_services_done=[
                    MonthlyServicesDone(
                        month=month_key,
                        services_done=completed_by_month[month_key],
                    )
                    for month_key in month_keys
                ],
            )

    async def get_tutor_id(self, user_id: UUID, session: AsyncSession) -> UUID | None:
        query = (
            select(UserRoleAssociation.tutor_id)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.tutor_id.is_not(None),
                func.lower(Role.slug) == "tutor",
            )
        )
        return (await session.execute(query)).scalar_one_or_none()

    async def get_student_id(self, user_id: UUID, session: AsyncSession) -> UUID | None:
        query = (
            select(UserRoleAssociation.student_id)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.student_id.is_not(None),
                func.lower(Role.slug) == "student",
            )
        )
        return (await session.execute(query)).scalar_one_or_none()

    async def get_tutor_dashboard(self, user_id: UUID) -> TutorDashboardData | None:
        async with get_session() as session:
            tutor_id = await self.get_tutor_id(user_id, session)
            if tutor_id is None:
                return None

            service_rows = (
                (
                    await session.execute(
                        select(Service).where(Service.tutor_id == tutor_id)
                    )
                )
                .scalars()
                .all()
            )
            booking_rows = (
                await session.execute(
                    select(ServiceBooking, Service)
                    .join(Service, Service.id == ServiceBooking.service_id)
                    .where(
                        Service.tutor_id == tutor_id,
                        ServiceBooking.status == BookingStatus.ACCEPTED.value,
                    )
                )
            ).all()
            now = datetime.now(timezone.utc)

            total_earnings = sum(
                float(service.price or 0) for _, service in booking_rows
            )
            unique_students = {booking.student_id for booking, _ in booking_rows}
            average_students = (
                len(booking_rows) / len(service_rows) if service_rows else 0.0
            )

            average_rating = (
                await session.execute(
                    select(func.avg(TutorReview.rating)).where(
                        TutorReview.tutor_id == tutor_id,
                    )
                )
            ).scalar_one()
            recent_reviews = (
                await session.execute(
                    select(func.count(TutorReview.id)).where(
                        TutorReview.tutor_id == tutor_id,
                        TutorReview.created_at >= now - timedelta(days=30),
                    )
                )
            ).scalar_one()

            bookings_by_service: dict[UUID, ServiceBooking] = {}
            booking_counts_by_service: dict[UUID, int] = {}
            for booking, service in booking_rows:
                current = bookings_by_service.get(service.id)
                booking_start = booking.scheduled_start_at.replace(tzinfo=timezone.utc)
                current_start = (
                    current.scheduled_start_at.replace(tzinfo=timezone.utc)
                    if current is not None
                    else None
                )
                if current_start is None or booking_start < current_start:
                    bookings_by_service[service.id] = booking
                booking_counts_by_service[service.id] = (
                    booking_counts_by_service.get(service.id, 0) + 1
                )

            def scheduled_start(service: Service) -> datetime:
                booking = bookings_by_service.get(service.id)
                if booking is not None:
                    return booking.scheduled_start_at.replace(tzinfo=timezone.utc)
                return service_datetime(service.date, service.time)

            upcoming = [
                service for service in service_rows if scheduled_start(service) > now
            ]
            upcoming.sort(key=scheduled_start)

            services = [
                UpcomingService(
                    booking_id=(
                        bookings_by_service.get(service.id).id
                        if bookings_by_service.get(service.id)
                        else None
                    ),
                    service_id=service.id,
                    service_name=service.service_name,
                    date=service.date,
                    time=service.time,
                    scheduled_start_at=scheduled_start(service),
                    price=service.price or 0,
                    enrolled_students_count=booking_counts_by_service.get(
                        service.id, 0
                    ),
                    student_id=(
                        bookings_by_service.get(service.id).student_id
                        if bookings_by_service.get(service.id)
                        else None
                    ),
                    tutor_id=service.tutor_id,
                )
                for service in upcoming
            ]
            return TutorDashboardData(
                cards=TutorDashboardCards(
                    total_services=len(service_rows),
                    upcoming_services=len(upcoming),
                    total_earnings=total_earnings,
                    total_unique_students_taught=len(unique_students),
                ),
                upcoming_services=services,
                performance=TutorDashboardPerformance(
                    average_rating=round(float(average_rating or 0) / 2, 2),
                    total_reviews_last_30_days=int(recent_reviews or 0),
                    average_students_per_session=round(average_students, 2),
                ),
            )

    async def get_student_dashboard(self, user_id: UUID) -> StudentDashboardData | None:
        async with get_session() as session:
            student_id = await self.get_student_id(user_id, session)
            if student_id is None:
                return None

            now = datetime.now()
            start_of_month = now.date().replace(day=1)
            if start_of_month.month == 12:
                start_of_next_month = date(start_of_month.year + 1, 1, 1)
            else:
                start_of_next_month = date(
                    start_of_month.year, start_of_month.month + 1, 1
                )

            booking_rows = (
                await session.execute(
                    select(ServiceBooking, Service)
                    .join(Service, Service.id == ServiceBooking.service_id)
                    .where(
                        ServiceBooking.student_id == student_id,
                        ServiceBooking.status == BookingStatus.ACCEPTED.value,
                    )
                )
            ).all()
            upcoming = [
                (booking, service)
                for booking, service in booking_rows
                if booking.scheduled_start_at.replace(tzinfo=None) > now
            ]
            current_month = [
                (booking, service)
                for booking, service in booking_rows
                if start_of_month
                <= booking.scheduled_start_at.date()
                < start_of_next_month
            ]

            available_tutors_query = select(func.count(Tutor.id)).where(
                Tutor.is_visible.is_(True),
                Tutor.accepting_requests.is_(True),
                func.upper(Tutor.approval_status).in_(("ACCEPTED", "APPROVED")),
            )
            available_tutors = (
                await session.execute(available_tutors_query)
            ).scalar_one()
            return StudentDashboardData(
                total_upcoming_services=len(upcoming),
                total_available_tutors=int(available_tutors or 0),
                services_in_current_month=len(current_month),
                tutors_in_current_month=len(
                    {service.tutor_id for _, service in current_month}
                ),
            )
