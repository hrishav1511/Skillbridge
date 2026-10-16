from datetime import datetime
import re
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from skillbridge.database.models.sqlalchemy.users import Gender, PhoneType
from skillbridge.utils.renderer import (
    BaseInModel,
    BaseOutModel,
    BaseQueryCriteria,
    BaseResponse,
    Status,
)

# TODO: Check if we can generate this automatically by the use of tools like sqlalchemy2strawbery
if TYPE_CHECKING:
    pass


class UserRegisterInput(BaseInModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    confirm_password: str
    role_id: UUID
    status: Optional[str] = None
    academic_program: Optional[str] = None
    bio: Optional[str] = None
    teaching_style: Optional[str] = None
    is_visible: Optional[bool] = None
    approval_status: Status | None = None
    accepting_requests: Optional[bool] = None
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
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must contain at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserRegisterOutput(BaseOutModel):
    id: UUID
    full_name: str
    email: str
    phone: str


class UserRegisterResponse(BaseResponse):
    data: UserRegisterOutput


class UserRegisterDataValidationResponse(BaseResponse):
    pass


class UserLoginInput(BaseModel):
    email: str
    password: str


class UserOutputObject(BaseModel):
    id: int
    name: str
    email: str


class UserLoginOutput(BaseOutModel):
    access_token: str
    refresh_token: str
    token_type: str
    data: UserOutputObject


class UserOutput(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    status: Optional[str] = None
    has_registered: Optional[bool] = None
    is_verified: Optional[bool] = None
    id: UUID | None = None


class UserLoginResponse(BaseResponse):
    data: UserLoginOutput


class UserLogoutInput(BaseModel):
    access_token: str
    refresh_token: str


class UserLogoutResponse(BaseResponse):
    pass


class UpdateUserOutput(BaseOutModel):
    full_name: str
    email: str
    has_registered: bool
    user_profile: dict | None = None
    phone: str | None = None


class UpdateUserInput(BaseModel):
    full_name: Optional[str] = None
    national_id: str | None = None
    city: str | None = None
    dob_str: str | None = None
    nationality: str | None = None


class UpdateUserResponse(BaseResponse):
    data: UpdateUserOutput


class UserProfileOutput(BaseOutModel):
    pass


class UserProfileResponse(BaseResponse):
    data: UserProfileOutput


class NewTokensInput(BaseModel):
    refresh_token: str


class NewTokensOutput(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class NewTokenResponse(BaseResponse):
    data: NewTokensOutput


class UserModel(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str | None = None
    auth_id: Optional[str] = None
    has_registered: Optional[bool] = None
    role_id: Optional[UUID] = None
    is_verified: Optional[bool] = None


class UpdateUserModel(BaseModel):
    full_name: str | None = None


class UserProfileModel(BaseModel):
    user_id: UUID
    nationality: str | None = None
    gender: str | None = None
    address: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    is_saudi_citizen: bool | None = False
    national_id: str | None = None
    dob: datetime | None = None
    passport_number: str | None = None
    visa_number: str | None = None
    border_number: str | None = None


class UpdateUserProfileModel(BaseModel):
    nationality: str | None = None
    gender: str | None = None
    address: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    is_saudi_citizen: bool | None = False
    national_id: str | None = None
    dob: datetime | None = None
    passport_number: str | None = None
    visa_number: str | None = None
    border_number: str | None = None


class PaginatedUsers(BaseResponse):
    data: List[UserOutput]


class GetUserOutput(BaseOutModel):
    name: str
    email: str
    has_registered: bool
    user_profile: dict | None = None
    phone: str | None = None


class GetUserResponse(BaseResponse):
    data: GetUserOutput


class UserQueryCriteria(BaseQueryCriteria):
    user_id: UUID | None = None
    email: str | None = None
    name: str | None = None
    email_or_phone: str | None = None


class DeleteUserOutput(BaseOutModel):
    name: str
    email: str
    phone: str | None = None


class DeleteUserResponse(BaseResponse):
    data: DeleteUserOutput | None = None


class GETPendingSocketRequestOutput(BaseModel):
    created_at: datetime | None = None
    event_name: str | None = None
    requester_room_id: str | None = None
    provider_room_id: str | None = None
    user_binding_id: str | None = None
    requester_id: str | None = None


class GETPendingSocketRequestsResponse(BaseResponse):
    data: List[GETPendingSocketRequestOutput] | None = None
