from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str  # user_id
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"
    jti: str  # JWT ID


class RefreshTokenModel(BaseModel):
    token: str
    user_id: UUID
    expires_at: datetime

class RefreshTokenRequestInput(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
