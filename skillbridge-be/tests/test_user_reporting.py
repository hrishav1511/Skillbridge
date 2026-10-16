from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy import select

from skillbridge.api.repositories.report import ServiceReportRepository, TutorReportRepository
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User


async def _add_admin(session):
    admin = User(id=uuid4(), full_name="Admin", email=f"{uuid4()}@example.com", password="x")
    role = Role(id=uuid4(), title="Admin", slug="admin")
    session.add_all([admin, role, UserRoleAssociation(user_id=admin.id, role_id=role.id)])
    await session.flush()
    return admin


@pytest.mark.asyncio
async def test_student_can_report_tutor_and_admin_can_list_and_discard(test_session):
    admin = await _add_admin(test_session)
    student = Student(id=uuid4())
    tutor = Tutor(id=uuid4(), academic_program="Computer Science")
    test_session.add_all([student, tutor])
    await test_session.flush()

    report = await TutorReportRepository().create_report(
        student_id=student.id,
        tutor_id=tutor.id,
        reason="Misleading profile",
        session=test_session,
    )

    assert report.student_id == student.id
    assert report.tutor_id == tutor.id
    assert report.reason == "Misleading profile"
    assert (await test_session.execute(
        select(Notification).where(
            Notification.user_id == admin.id,
            Notification.notification_type == "TUTOR_REPORTED",
        )
    )).scalar_one()

    reports = await TutorReportRepository().list_reports(session=test_session)
    assert len(reports) == 1

    await TutorReportRepository().discard_report(report.id, session=test_session)
    remaining = await TutorReportRepository().list_reports(session=test_session)
    assert remaining == []


@pytest.mark.asyncio
async def test_student_can_report_service_and_admin_can_disable_service_and_discard(test_session):
    admin = await _add_admin(test_session)
    student = Student(id=uuid4())
    tutor = Tutor(id=uuid4(), academic_program="Mathematics")
    service = Service(
        id=uuid4(),
        tutor_id=tutor.id,
        service_name="Calculus Bootcamp",
        description="Needs improvement",
        date=date.today(),
        time=time(12, 0),
        price=40,
        level=ServiceLevel.BEGINNER,
    )
    test_session.add_all([student, tutor, service])
    await test_session.flush()

    report = await ServiceReportRepository().create_report(
        student_id=student.id,
        service_id=service.id,
        reason="Spam content",
        session=test_session,
    )

    assert report.student_id == student.id
    assert report.service_id == service.id
    assert report.reason == "Spam content"
    assert (await test_session.execute(
        select(Notification).where(
            Notification.user_id == admin.id,
            Notification.notification_type == "SERVICE_REPORTED",
        )
    )).scalar_one()

    disabled = await ServiceReportRepository().disable_service(service.id, session=test_session)
    assert disabled.status == "INACTIVE"

    reports = await ServiceReportRepository().list_reports(session=test_session)
    assert len(reports) == 1

    await ServiceReportRepository().discard_report(report.id, session=test_session)
    assert await ServiceReportRepository().list_reports(session=test_session) == []
