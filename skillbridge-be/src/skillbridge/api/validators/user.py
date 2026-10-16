from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import status
from pydantic import BaseModel, EmailStr, field_validator, model_validator

from skillbridge.database.models.sqlalchemy.users import Gender, PhoneType
from skillbridge.exceptions import InvalidCredentialsError
from skillbridge.utils.renderer import BaseQueryCriteria, Status


class CreateUserValidator(BaseModel):
    name: str
    email: EmailStr
    password: str
    role_id: int


class UpdateUserInputValidator(BaseModel):
    name: str | None = None
    national_id: str | None = None
    city: str | None = None
    dob: date | None = None
    user_id: UUID
    nationality: str | None = None


class UserRegisterInputValidator(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    confirm_password: str
    role_id: UUID
    status: Optional[str] = None
    has_registered: Optional[bool] = True
    is_verified: Optional[bool] = True
    academic_program: Optional[str] = None
    bio: Optional[str] = None
    teaching_style: Optional[str] = None
    is_visible: Optional[bool] = None
    approval_status: Status | None = None
    accepting_requests: Optional[bool] = True
    tags: list[str] | None = None
    field_of_study: Optional[str] = None
    enrolled_university: Optional[str] = None
    graduation_year: Optional[int] = None

    @field_validator("email")
    @classmethod
    def validate_fulda_email(cls, value: EmailStr) -> str:
        normalized = str(value).strip().lower()
        if not normalized.endswith("@hs-fulda.de"):
            raise ValueError("Registration requires an @hs-fulda.de email address")
        return normalized

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.password != self.confirm_password:
            raise InvalidCredentialsError(
                message="Your passwords do not match.",
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
            )
        return self


class UserSearchValidator(BaseQueryCriteria):
    user_id: UUID | None = None
    email: str | None = None
    name: str | None = None
    email_or_phone: str | None = None
