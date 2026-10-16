from fastapi import APIRouter, status

from skillbridge.api.repositories.auth.login import LoginRepository
from skillbridge.api.schemas.login import (
    LoginInput,
    LoginOutput,
    LoginResponse,
    LoginUserOutput,
    LoginRoleOutput,
)
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.login import LoginInputValidator
from skillbridge.exceptions import handle_exceptions
from skillbridge.api.repositories.auth.config import auth_config
router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
    response_model_by_alias=False,
)
@handle_exceptions
async def login(*, login_data: LoginInput) -> LoginResponse:
    has_error, login_data = BaseValidator.validate(
        validator=LoginInputValidator,
        input_data=login_data,
    )
    if has_error:
        return has_error

    user_data, tokens = await LoginRepository().login(login_data)
    
    return LoginResponse(
        success=True,
        message="User logged in successfully.",
        data=LoginOutput(
            user_id=user_data.user_id,
            role_id=user_data.role_id,
            tutor_id=(
                user_data.tutor_id
                if user_data.tutor_id
                and user_data.ura_role.slug == "tutor"
                else None
            ),
            student_id=(
                user_data.student_id
                if user_data.student_id
                and user_data.ura_role.slug == "student"
                else None
            ),
            profile_picture_url=(
                getattr(user_data.ura_tutor, "profile_picture_url", None)
                or getattr(user_data.ura_student, "profile_picture_url", None)
            ),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=LoginUserOutput(
                id=user_data.ura_user.id,
                full_name=user_data.ura_user.full_name,
                email=user_data.ura_user.email,
                phone=user_data.ura_user.phone,
                has_registered=user_data.ura_user.has_registered,
                is_verified=user_data.ura_user.is_verified,
            ),
            role=LoginRoleOutput(
                id=user_data.ura_role.id,
                title=user_data.ura_role.title,
                slug=user_data.ura_role.slug,
                description=user_data.ura_role.description,
            ),
        ),
    )
