from contextlib import asynccontextmanager
from datetime import date, time
from uuid import uuid4

import pytest

from skillbridge.api.repositories import service_attachment as attachment_repository
from skillbridge.api.repositories.service_attachment import ServiceAttachmentRepository
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_attachments import ServiceAttachment
from skillbridge.database.models.sqlalchemy.service_bookings import BookingStatus, ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.utils.service_time import service_datetime


@pytest.fixture
def attachment_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(attachment_repository, "get_session", session_context)
    return test_session


@pytest.mark.asyncio
async def test_service_attachment_access_is_limited_to_tutor_or_booked_student(attachment_session):
    tutor_user = User(id=uuid4(), full_name="Tutor", email="tutor@example.com", password="x")
    student_user = User(id=uuid4(), full_name="Student", email="student@example.com", password="x")
    other_user = User(id=uuid4(), full_name="Other", email="other@example.com", password="x")
    tutor = Tutor(id=uuid4(), approval_status="ACCEPTED")
    student = Student(id=uuid4())
    tutor_role = Role(id=uuid4(), title="TUTOR", slug="tutor")
    student_role = Role(id=uuid4(), title="STUDENT", slug="student")
    service = Service(
        id=uuid4(),
        tutor_id=tutor.id,
        service_name="Python",
        price=10,
        level=ServiceLevel.BEGINNER,
        date=date.today(),
        time=time(12, 0),
    )
    attachment = ServiceAttachment(
        id=uuid4(),
        service_id=service.id,
        tutor_id=tutor.id,
        object_key="tutor-media/service-attachments/file.pdf",
        original_filename="file.pdf",
        content_type="application/pdf",
        file_size=10,
    )
    attachment_session.add_all(
        [
            tutor_user,
            student_user,
            other_user,
            tutor,
            student,
            tutor_role,
            student_role,
            service,
            attachment,
            UserRoleAssociation(
                user_id=tutor_user.id,
                role_id=tutor_role.id,
                tutor_id=tutor.id,
            ),
            UserRoleAssociation(
                user_id=student_user.id,
                role_id=student_role.id,
                student_id=student.id,
            ),
            ServiceBooking(
                service_id=service.id,
                student_id=student.id,
                status=BookingStatus.ACCEPTED.value,
                scheduled_start_at=service_datetime(service.date, service.time),
            ),
        ]
    )
    await attachment_session.flush()

    repository = ServiceAttachmentRepository()
    assert await repository.get_for_user(
        attachment_id=attachment.id,
        user_id=tutor_user.id,
    )
    assert await repository.get_for_user(
        attachment_id=attachment.id,
        user_id=student_user.id,
    )
    assert await repository.get_for_user(
        attachment_id=attachment.id,
        user_id=other_user.id,
    ) is None


@pytest.mark.asyncio
async def test_created_attachment_can_be_serialized_after_repository_session_closes(
    attachment_session,
):
    attachment = await ServiceAttachmentRepository().create(
        service_id=uuid4(),
        tutor_id=uuid4(),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=12,
        object_key="tutor-media/service-attachments/notes.pdf",
    )

    payload = attachment.to_dict()

    assert payload["id"] == attachment.id
    assert payload["created_at"] is not None
