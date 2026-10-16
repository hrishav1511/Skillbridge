from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from skillbridge.api.schemas.user import UserRegisterInput
from skillbridge.database.models.sqlalchemy.users import User


def _registration(email: str) -> UserRegisterInput:
    return UserRegisterInput(
        full_name="Fulda Student",
        email=email,
        password="Secure123!",
        confirm_password="Secure123!",
        role_id=uuid4(),
    )


def test_registration_accepts_and_normalizes_fulda_email():
    registration = _registration("Student.Name@HS-FULDA.DE")

    assert registration.email == "student.name@hs-fulda.de"


@pytest.mark.parametrize("email", ["student@gmail.com", "student@example.com"])
def test_registration_rejects_non_fulda_email(email):
    with pytest.raises(ValidationError, match="@hs-fulda.de"):
        _registration(email)


def test_registration_rejects_malformed_email():
    with pytest.raises(ValidationError):
        _registration("not-an-email")


def test_registration_requires_backend_password_policy():
    with pytest.raises(ValidationError, match="at least 8 characters"):
        UserRegisterInput(
            full_name="Fulda Student",
            email="student@hs-fulda.de",
            password="S1!a",
            confirm_password="S1!a",
            role_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_database_rejects_duplicate_normalized_email(test_session):
    test_session.add_all(
        [
            User(full_name="First", email="duplicate@hs-fulda.de", password="hash"),
            User(full_name="Second", email="duplicate@hs-fulda.de", password="hash"),
        ]
    )

    with pytest.raises(IntegrityError):
        await test_session.flush()
