from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.reported_services import ReportedService
from skillbridge.database.models.sqlalchemy.reported_tutors import ReportedTutor
from skillbridge.database.models.sqlalchemy.reported_reviews import ReportedReview
from skillbridge.database.models.sqlalchemy.service_reviews import ServiceReview
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.utils.renderer import Status


async def _notify_admins(
    session: AsyncSession,
    *,
    notification_type: str,
    title: str,
    message: str,
    data: dict,
) -> None:
    notification_repository = NotificationRepository()
    for admin_user_id in await notification_repository.admin_user_ids(session=session):
        await notification_repository.create_for_user(
            user_id=admin_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            session=session,
        )


class TutorReportRepository(BaseRepository):
    model = ReportedTutor

    async def create_report(
        self,
        student_id: UUID,
        tutor_id: UUID,
        reason: str,
        session: AsyncSession = None,
    ):
        if session is None:
            async with get_session() as create_session:
                report = await self.create_report(
                    student_id=student_id,
                    tutor_id=tutor_id,
                    reason=reason,
                    session=create_session,
                )
                await create_session.commit()
                return report

        report = self.model(
            student_id=student_id,
            tutor_id=tutor_id,
            reason=reason,
        )
        session.add(report)
        await session.flush()
        await session.refresh(report)
        await _notify_admins(
            session,
            notification_type="TUTOR_REPORTED",
            title="New tutor report",
            message="A tutor report requires moderation.",
            data={"report_id": str(report.id), "tutor_id": str(tutor_id)},
        )
        return report

    async def list_reports(self, session: AsyncSession = None):
        if session is None:
            async with get_session() as query_session:
                return await self.list_reports(session=query_session)

        # Join the names in here so the admin panel renders people rather than
        # UUIDs, and does not need one extra request per row to do it.
        result = await session.execute(
            select(self.model)
            .options(
                joinedload(self.model.reported_tutor_tutor)
                .joinedload(Tutor.tutor_ura)
                .joinedload(UserRoleAssociation.ura_user),
                joinedload(self.model.reported_tutor_student)
                .joinedload(Student.student_ura)
                .joinedload(UserRoleAssociation.ura_user),
            )
            .order_by(self.model.created_at.desc())
        )
        return result.unique().scalars().all()

    async def discard_report(self, report_id: UUID, session: AsyncSession = None):
        if session is None:
            async with get_session() as update_session:
                result = await self.discard_report(report_id=report_id, session=update_session)
                await update_session.commit()
                return result

        report = await session.get(self.model, report_id)
        if not report:
            raise ValueError("Tutor report not found.")
        await session.delete(report)
        await session.flush()
        return True

    async def disable_tutor(self, tutor_id: UUID, session: AsyncSession = None):
        if session is None:
            async with get_session() as update_session:
                tutor = await self.disable_tutor(tutor_id=tutor_id, session=update_session)
                await update_session.commit()
                return tutor

        tutor = await session.get(Tutor, tutor_id)
        if not tutor:
            raise ValueError("Tutor not found.")
        tutor.status = Status.INACTIVE
        tutor.is_visible = False
        tutor.accepting_requests = False
        await session.flush()
        return tutor


class ServiceReportRepository(BaseRepository):
    model = ReportedService

    async def create_report(
        self,
        student_id: UUID,
        service_id: UUID,
        reason: str,
        session: AsyncSession = None,
    ):
        if session is None:
            async with get_session() as create_session:
                report = await self.create_report(
                    student_id=student_id,
                    service_id=service_id,
                    reason=reason,
                    session=create_session,
                )
                await create_session.commit()
                return report

        report = self.model(
            student_id=student_id,
            service_id=service_id,
            reason=reason,
        )
        session.add(report)
        await session.flush()
        await session.refresh(report)
        await _notify_admins(
            session,
            notification_type="SERVICE_REPORTED",
            title="New service report",
            message="A service report requires moderation.",
            data={"report_id": str(report.id), "service_id": str(service_id)},
        )
        return report

    async def list_reports(self, session: AsyncSession = None):
        if session is None:
            async with get_session() as query_session:
                return await self.list_reports(session=query_session)

        # Same reasoning as the tutor reports: resolve names server-side.
        result = await session.execute(
            select(self.model)
            .options(
                joinedload(self.model.reported_service_service),
                joinedload(self.model.reported_service_student)
                .joinedload(Student.student_ura)
                .joinedload(UserRoleAssociation.ura_user),
            )
            .order_by(self.model.created_at.desc())
        )
        return result.unique().scalars().all()

    async def discard_report(self, report_id: UUID, session: AsyncSession = None):
        if session is None:
            async with get_session() as update_session:
                result = await self.discard_report(report_id=report_id, session=update_session)
                await update_session.commit()
                return result

        report = await session.get(self.model, report_id)
        if not report:
            raise ValueError("Service report not found.")
        await session.delete(report)
        await session.flush()
        return True

    async def disable_service(self, service_id: UUID, session: AsyncSession = None):
        if session is None:
            async with get_session() as update_session:
                service = await self.disable_service(service_id=service_id, session=update_session)
                await update_session.commit()
                return service

        service = await session.get(Service, service_id)
        if not service:
            raise ValueError("Service not found.")
        service.status = Status.INACTIVE
        await session.flush()
        return service


class ReviewReportRepository(BaseRepository):
    model = ReportedReview

    @staticmethod
    def _review_model(review_type: str):
        normalized = review_type.strip().lower()
        if normalized == "tutor":
            return normalized, TutorReview, "tutor_review_id"
        if normalized == "service":
            return normalized, ServiceReview, "service_review_id"
        raise HTTPException(status_code=422, detail="review_type must be tutor or service.")

    async def create_report(
        self,
        *,
        reporter_user_id: UUID,
        review_type: str,
        review_id: UUID,
        reason: str,
    ):
        normalized, review_model, target_column = self._review_model(review_type)
        async with get_session() as session:
            review = await session.get(review_model, review_id)
            if review is None:
                raise HTTPException(status_code=404, detail="Review not found.")
            existing_report = (
                await session.execute(
                    select(ReportedReview.id).where(
                        ReportedReview.reporter_user_id == reporter_user_id,
                        getattr(ReportedReview, target_column) == review_id,
                    )
                )
            ).scalar_one_or_none()
            if existing_report is not None:
                raise HTTPException(
                    status_code=409, detail="You already reported this review."
                )
            report = ReportedReview(
                reporter_user_id=reporter_user_id,
                reason=reason,
                **{target_column: review_id},
            )
            session.add(report)
            try:
                await session.flush()
                await session.refresh(report)
                await _notify_admins(
                    session,
                    notification_type="REVIEW_REPORTED",
                    title="New review report",
                    message="A review report requires moderation.",
                    data={
                        "report_id": str(report.id),
                        "review_id": str(review_id),
                        "review_type": normalized,
                    },
                )
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=409, detail="You already reported this review."
                ) from exc
            return report, review, normalized

    async def list_reports(self):
        async with get_session() as session:
            result = await session.execute(
                select(ReportedReview)
                .options(
                    joinedload(ReportedReview.reported_tutor_review),
                    joinedload(ReportedReview.reported_service_review),
                    # The moderation table shows who filed the report, so the
                    # reporter has to come back with it rather than be lazily
                    # loaded outside the session.
                    joinedload(ReportedReview.reporter_user),
                )
                .execution_options(populate_existing=True)
                .order_by(ReportedReview.reported_at.desc())
            )
            return list(result.scalars().unique().all())

    async def discard_report(self, report_id: UUID):
        async with get_session() as session:
            report = await session.get(ReportedReview, report_id)
            if report is None:
                raise HTTPException(status_code=404, detail="Review report not found.")
            reporter_user_id = report.reporter_user_id
            await session.delete(report)
            await NotificationRepository().create_for_user(
                user_id=reporter_user_id,
                notification_type="REVIEW_REPORT_DISMISSED",
                title="Review report reviewed",
                message="Your review report was dismissed after moderation.",
                data={"report_id": str(report_id)},
                session=session,
            )
            await session.commit()

    async def remove_reported_review(self, report_id: UUID):
        async with get_session() as session:
            report = (
                await session.execute(
                    select(ReportedReview)
                    .where(ReportedReview.id == report_id)
                    .options(
                        joinedload(ReportedReview.reported_tutor_review),
                        joinedload(ReportedReview.reported_service_review),
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if report is None:
                raise HTTPException(status_code=404, detail="Review report not found.")
            if report.tutor_review_id is not None:
                review = await session.get(TutorReview, report.tutor_review_id)
            else:
                review = await session.get(ServiceReview, report.service_review_id)
            if review is None:
                raise HTTPException(status_code=404, detail="Reported review not found.")
            reviewer_user_id = (
                await session.execute(
                    select(UserRoleAssociation.user_id).where(
                        UserRoleAssociation.student_id == review.student_id
                    )
                )
            ).scalar_one_or_none()
            review_id = review.id
            await session.execute(
                delete(ReportedReview).where(
                    or_(
                        ReportedReview.tutor_review_id == review_id,
                        ReportedReview.service_review_id == review_id,
                    )
                )
            )
            await session.flush()
            await session.delete(review)
            if reviewer_user_id is not None:
                await NotificationRepository().create_for_user(
                    user_id=reviewer_user_id,
                    notification_type="REVIEW_REMOVED",
                    title="Review removed",
                    message="One of your reviews was removed after moderation.",
                    data={"review_id": str(review_id)},
                    session=session,
                )
            await session.commit()
            return review_id
