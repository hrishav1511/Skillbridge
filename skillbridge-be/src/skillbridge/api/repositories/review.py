from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.filters.review import ServiceReviewSearchFilter, TutorReviewSearchFilter
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.schemas.review import ServiceReviewQueryCriteria, TutorReviewQueryCriteria
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.service_reviews import ServiceReview
from skillbridge.database.models.sqlalchemy.service_bookings import BookingStatus, ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.utils.service_time import service_datetime


class ReviewRepository:
    @staticmethod
    def _booking_completed(row, now: datetime) -> bool:
        start = row.scheduled_start_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        duration = timedelta(0)
        if row.end_time is not None:
            duration = datetime.combine(date.min, row.end_time) - datetime.combine(
                date.min, row.time
            )
        return start + max(duration, timedelta(0)) <= now

    async def ensure_tutor_review_allowed(
        self,
        tutor_id: UUID,
        student_id: UUID,
        session: AsyncSession | None = None,
    ) -> None:
        if session is None:
            async with get_session() as review_session:
                return await self.ensure_tutor_review_allowed(
                    tutor_id=tutor_id, student_id=student_id, session=review_session
                )
        schedules = (
            await session.execute(
                select(
                    ServiceBooking.scheduled_start_at,
                    Service.time,
                    Service.end_time,
                )
                .join(ServiceBooking, ServiceBooking.service_id == Service.id)
                .where(
                    Service.tutor_id == tutor_id,
                    ServiceBooking.student_id == student_id,
                    ServiceBooking.status == BookingStatus.ACCEPTED.value,
                )
            )
        ).all()
        now = datetime.now(timezone.utc)
        if not any(self._booking_completed(row, now) for row in schedules):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can review this tutor only after completing one of their services.",
            )

    async def ensure_service_review_allowed(
        self,
        service_id: UUID,
        student_id: UUID,
        session: AsyncSession | None = None,
    ) -> None:
        if session is None:
            async with get_session() as create_session:
                await self.ensure_service_review_allowed(
                    service_id=service_id,
                    student_id=student_id,
                    session=create_session,
                )
                return

        result = await session.execute(
            select(
                ServiceBooking.scheduled_start_at,
                Service.time,
                Service.end_time,
            )
            .join(ServiceBooking, ServiceBooking.service_id == Service.id)
            .where(
                ServiceBooking.service_id == service_id,
                ServiceBooking.student_id == student_id,
                ServiceBooking.status == BookingStatus.ACCEPTED.value,
            )
        )
        service_schedule = result.first()
        if service_schedule is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can review only a service you booked.",
            )

        if not self._booking_completed(service_schedule, datetime.now(timezone.utc)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can review this service only after it is completed.",
            )

    async def create_tutor_review(self, payload: dict[str, Any], session: AsyncSession | None = None):
        if session is None:
            async with get_session() as create_session:
                try:
                    result = await self.create_tutor_review(payload=payload, session=create_session)
                    await create_session.commit()
                    return result
                except IntegrityError as exc:
                    await create_session.rollback()
                    raise HTTPException(status_code=409, detail="You already reviewed this tutor.") from exc

        review = TutorReview(**payload)
        session.add(review)
        await session.flush()
        await session.refresh(review)
        tutor_user_id = (
            await session.execute(
                select(UserRoleAssociation.user_id).where(
                    UserRoleAssociation.tutor_id == review.tutor_id
                )
            )
        ).scalar_one_or_none()
        if tutor_user_id is not None:
            await NotificationRepository().create_for_user(
                user_id=tutor_user_id,
                notification_type="TUTOR_REVIEW_CREATED",
                title="New tutor review",
                message="A student left a new review on your tutor profile.",
                data={"review_id": str(review.id), "tutor_id": str(review.tutor_id)},
                session=session,
            )
        return {"success": True, "message": "Tutor review created.", "data": review}

    async def create_service_review(self, payload: dict[str, Any], session: AsyncSession | None = None):
        if session is None:
            async with get_session() as create_session:
                try:
                    result = await self.create_service_review(payload=payload, session=create_session)
                    await create_session.commit()
                    return result
                except IntegrityError as exc:
                    await create_session.rollback()
                    raise HTTPException(status_code=409, detail="You already reviewed this service.") from exc

        review = ServiceReview(**payload)
        session.add(review)
        await session.flush()
        await session.refresh(review)
        tutor_user_id = (
            await session.execute(
                select(UserRoleAssociation.user_id)
                .join(Service, Service.tutor_id == UserRoleAssociation.tutor_id)
                .where(Service.id == review.service_id)
            )
        ).scalar_one_or_none()
        if tutor_user_id is not None:
            await NotificationRepository().create_for_user(
                user_id=tutor_user_id,
                notification_type="SERVICE_REVIEW_CREATED",
                title="New service review",
                message="A student left a new review on your service.",
                data={
                    "review_id": str(review.id),
                    "service_id": str(review.service_id),
                },
                session=session,
            )
        return {"success": True, "message": "Service review created.", "data": review}

    async def get_tutor_average_rating(self, tutor_id: UUID, session: AsyncSession | None = None):
        if session is None:
            async with get_session() as create_session:
                return await self.get_tutor_average_rating(tutor_id=tutor_id, session=create_session)

        result = await session.execute(
            select(func.avg(TutorReview.rating)).where(TutorReview.tutor_id == tutor_id)
        )
        average = result.scalar_one_or_none()
        return average

    async def get_service_average_rating(self, service_id: UUID, session: AsyncSession | None = None):
        if session is None:
            async with get_session() as create_session:
                return await self.get_service_average_rating(service_id=service_id, session=create_session)

        result = await session.execute(
            select(func.avg(ServiceReview.rating)).where(ServiceReview.service_id == service_id)
        )
        average = result.scalar_one_or_none()
        return average

    async def list_tutor_reviews(self, tutor_id: UUID | None = None, session: AsyncSession | None = None):
        if session is None:
            async with get_session() as create_session:
                return await self.list_tutor_reviews(tutor_id=tutor_id, session=create_session)

        query = select(TutorReview)
        if tutor_id is not None:
            query = query.where(TutorReview.tutor_id == tutor_id)

        result = await session.execute(query.order_by(TutorReview.created_at.desc()))
        reviews = result.scalars().all()
        return {"success": True, "message": "Tutor reviews fetched.", "data": reviews}

    async def list_service_reviews(self, service_id: UUID | None = None, session: AsyncSession | None = None):
        if session is None:
            async with get_session() as create_session:
                return await self.list_service_reviews(service_id=service_id, session=create_session)

        query = select(ServiceReview)
        if service_id is not None:
            query = query.where(ServiceReview.service_id == service_id)

        result = await session.execute(query.order_by(ServiceReview.created_at.desc()))
        reviews = result.scalars().all()
        return {"success": True, "message": "Service reviews fetched.", "data": reviews}

    async def filter_tutor_reviews(self, query_criteria: TutorReviewQueryCriteria):
        search_filter = await TutorReviewSearchFilter(query_criteria)
        search_query = await search_filter.get_query()
        async with get_session() as session:
            result = await session.execute(search_query)
            reviews = result.scalars().unique().all()
            return {"success": True, "message": "Tutor reviews fetched.", "data": reviews}

    async def filter_service_reviews(self, query_criteria: ServiceReviewQueryCriteria):
        search_filter = await ServiceReviewSearchFilter(query_criteria)
        search_query = await search_filter.get_query()
        async with get_session() as session:
            result = await session.execute(search_query)
            reviews = result.scalars().unique().all()
            return {"success": True, "message": "Service reviews fetched.", "data": reviews}


def format_average_rating(value: float | None) -> str:
    if value is None:
        return "No Review Yet"
    return f"{round(float(value), 1)}/10"
