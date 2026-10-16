from pydantic import BaseModel, EmailStr, field_validator

from skillbridge.utils.renderer import BaseInModel, BaseOutModel, BaseResponse
from uuid import UUID


class LoginUserOutput(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone: str | None = None
    has_registered: bool | None = None
    is_verified: bool | None = None


class LoginRoleOutput(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None = None


class LoginInput(BaseModel):
    email: str
    password: str
    role_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginOutput(BaseOutModel):
    user_id: UUID
    role_id: UUID
    user: LoginUserOutput
    role: LoginRoleOutput
    tutor_id: UUID | None = None
    student_id: UUID | None = None
    # Present for whichever role carries one; null for roles that have no
    # profile picture (admins), so the navbar can fall back to initials.
    profile_picture_url: str | None = None
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseResponse):
    data: LoginOutput


class CodeInput(BaseInModel):
    code: str
    redirect_uri: str


class TokensForCodeOutput(BaseOutModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


class TokensForCodeResponse(BaseResponse):
    data: TokensForCodeOutput
