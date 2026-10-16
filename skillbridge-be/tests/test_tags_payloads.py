from datetime import date, time
from uuid import uuid4

import pytest

from skillbridge.api.schemas.service import CreateServiceInput, UpdateServiceInput
from skillbridge.api.schemas.tutor import CreateTutorInput, UpdateTutorInput
from skillbridge.api.schemas.user import UserRegisterInput


def test_user_register_input_accepts_tags():
    payload = UserRegisterInput(
        full_name="Test Tutor",
        email="tutor@hs-fulda.de",
        phone="1234567890",
        password="Secret123!",
        confirm_password="Secret123!",
        role_id=uuid4(),
        tags=["python", "algorithms"],
    )

    assert payload.tags == ["python", "algorithms"]


def test_tutor_create_and_update_inputs_accept_tags():
    create_payload = CreateTutorInput(user_id=uuid4(), tags=["react", "ui"])
    update_payload = UpdateTutorInput(tags=["backend", "api"])

    assert create_payload.tags == ["react", "ui"]
    assert update_payload.tags == ["backend", "api"]


def test_service_create_and_update_inputs_accept_tags():
    create_payload = CreateServiceInput(
        tutor_id=uuid4(),
        service_name="Python Basics",
        description="Intro class",
        date=date(2026, 7, 17),
        time=time(14, 30),
        price=50,
        level="BEGINNER",
        tags=["python", "beginner"],
    )
    update_payload = UpdateServiceInput(tags=["advanced", "data-structures"])

    assert create_payload.tags == ["python", "beginner"]
    assert update_payload.tags == ["advanced", "data-structures"]
