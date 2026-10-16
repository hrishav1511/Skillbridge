from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class LoginInputValidator(BaseModel):
    email: EmailStr
    password: str
    role_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()
