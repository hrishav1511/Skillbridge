from datetime import datetime, timezone
from uuid import uuid4

from skillbridge.api.schemas.service import ServiceOutput
from skillbridge.api.schemas.service_booking import ServiceBookingOutput
from skillbridge.api.schemas.student import StudentOutput
from skillbridge.api.schemas.tutor import TutorOutput
from skillbridge.api.validators.service import ServiceLevel


def test_service_booking_output_accepts_nested_service_and_student():
    booking_id = uuid4()
    service_id = uuid4()
    student_id = uuid4()

    payload = ServiceBookingOutput(
        id=booking_id,
        status="PENDING",
        scheduled_start_at=datetime.now(timezone.utc),
        service=ServiceOutput(
            id=service_id,
            tutor_id=uuid4(),
            service_name="Python Basics",
            description="Intro session",
            date=None,
            time=None,
            price=25,
            level=ServiceLevel.BEGINNER,
            joining_link=None,
            image_urls=None,
            video_url=None,
            video_urls=None,
            tags=None,
            approval_status="ACCEPTED",
            rejection_reason=None,
            tutor=None,
        ),
        student=StudentOutput(
            id=student_id,
            field_of_study="Computer Science",
            enrolled_university="Fulda University",
            graduation_year=2026,
            user=None,
        ),
        tutor=TutorOutput(
            id=uuid4(),
            academic_program="Computer Science",
            bio="Teaching Python",
            phone=None,
            teaching_style="Interactive",
            is_visible=True,
            approval_status="ACCEPTED",
            accepting_requests=True,
            tags=None,
            user=None,
            profile_picture_url=None,
            cover_picture_url=None,
        ),
    )

    assert payload.service.id == service_id
    assert payload.student.id == student_id
    assert payload.tutor is not None
    assert payload.tutor.academic_program == "Computer Science"
