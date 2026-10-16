from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from unittest.mock import AsyncMock

from skillbridge.api.api_v1.endpoints.report import _ensure_admin
from skillbridge.api.repositories import report as report_repository
from skillbridge.api.repositories.report import ReviewReportRepository
from skillbridge.api.repositories.review import ReviewRepository
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.schemas.report import CreateReviewReportInput
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.reported_reviews import ReportedReview
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_reviews import ServiceReview
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User


@pytest.fixture
def review_report_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(report_repository, "get_session", session_context)
    return test_session


async def _seed_reviews(session):
    reporter = User(id=uuid4(), full_name="Reporter", email="reporter@hs-fulda.de", password="x")
    reviewer = User(id=uuid4(), full_name="Reviewer", email="reviewer@hs-fulda.de", password="x")
    admin = User(id=uuid4(), full_name="Admin", email="admin@hs-fulda.de", password="x")
    admin_role = Role(id=uuid4(), title="Admin", slug="admin")
    student = Student(id=uuid4())
    tutor = Tutor(id=uuid4())
    tutor_review = TutorReview(
        id=uuid4(), tutor_id=tutor.id, student_id=student.id,
        rating=8, comment="Helpful but inaccurate material",
    )
    service_review = ServiceReview(
        id=uuid4(), service_id=uuid4(), student_id=student.id,
        rating=4, comment="Service review content",
    )
    session.add_all([
        reporter, reviewer, admin, admin_role, student, tutor, tutor_review, service_review,
        UserRoleAssociation(user_id=reviewer.id, role_id=uuid4(), student_id=student.id),
        UserRoleAssociation(user_id=admin.id, role_id=admin_role.id),
    ])
    await session.flush()
    return reporter, reviewer, admin, tutor_review, service_review


def test_review_report_reason_rejects_whitespace():
    with pytest.raises(ValueError):
        CreateReviewReportInput(reason="              ")


@pytest.mark.asyncio
async def test_review_report_admin_queue_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(
        UserRoleAssociationRepository,
        "is_user_admin",
        AsyncMock(return_value=False),
    )
    with pytest.raises(HTTPException) as forbidden:
        await _ensure_admin(uuid4())
    assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_create_list_duplicate_and_dismiss_review_report(review_report_session):
    reporter, _, admin, tutor_review, _ = await _seed_reviews(review_report_session)
    repository = ReviewReportRepository()
    report, review, review_type = await repository.create_report(
        reporter_user_id=reporter.id,
        review_type="tutor",
        review_id=tutor_review.id,
        reason="This review contains abusive wording.",
    )
    assert review.id == tutor_review.id
    assert review_type == "tutor"
    assert [item.id for item in await repository.list_reports()] == [report.id]
    assert (await review_report_session.execute(
        select(Notification).where(
            Notification.user_id == admin.id,
            Notification.notification_type == "REVIEW_REPORTED",
        )
    )).scalar_one()

    with pytest.raises(HTTPException) as duplicate:
        await repository.create_report(
            reporter_user_id=reporter.id,
            review_type="tutor",
            review_id=tutor_review.id,
            reason="This is the same report submitted twice.",
        )
    assert duplicate.value.status_code == 409

    await repository.discard_report(report.id)
    assert await review_report_session.get(TutorReview, tutor_review.id) is not None
    assert await review_report_session.get(ReportedReview, report.id) is None


@pytest.mark.asyncio
async def test_missing_review_and_remove_moderation(review_report_session):
    reporter, reviewer, _, tutor_review, _ = await _seed_reviews(review_report_session)
    repository = ReviewReportRepository()
    with pytest.raises(HTTPException) as missing:
        await repository.create_report(
            reporter_user_id=reporter.id,
            review_type="tutor",
            review_id=uuid4(),
            reason="This missing review should not be reportable.",
        )
    assert missing.value.status_code == 404

    first, _, _ = await repository.create_report(
        reporter_user_id=reporter.id,
        review_type="tutor",
        review_id=tutor_review.id,
        reason="This review requires administrator attention.",
    )
    tutor_id = tutor_review.tutor_id
    await repository.remove_reported_review(first.id)
    assert await review_report_session.get(TutorReview, tutor_review.id) is None
    assert await ReviewRepository().get_tutor_average_rating(
        tutor_id, session=review_report_session
    ) is None
    report_count = (
        await review_report_session.execute(select(func.count(ReportedReview.id)))
    ).scalar_one()
    assert report_count == 0
    removal_notice = (
        await review_report_session.execute(
            select(Notification).where(
                Notification.user_id == reviewer.id,
                Notification.notification_type == "REVIEW_REMOVED",
            )
        )
    ).scalar_one()
    assert removal_notice.data["review_id"] == str(tutor_review.id)
