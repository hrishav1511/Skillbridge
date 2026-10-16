from datetime import datetime

from fastapi import APIRouter, status

from skillbridge.api.schemas.login import LoginResponse
from skillbridge.api.repositories.auth.register import RegisterRepository
from skillbridge.api.schemas.user import (
    UserRegisterDataValidationResponse,
    UserRegisterInput,
    UserRegisterOutput,
    UserRegisterResponse,
)
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_200_OK,  # fastapi post request automatically returns a 201 created status code unless explicitly changed this way
    response_model=UserRegisterResponse,  # validate the function response and strip out the extra fields returned if any
    response_model_by_alias=False,  #
)
@handle_exceptions
async def register(
    *, register_data: UserRegisterInput
) -> (
    UserRegisterResponse
):  # * for forcing the keyword arguments (register_data = some_data)
    has_error, register_data = BaseValidator.validate(
        validator=UserRegisterInputValidator,
        input_data=register_data,
    )

    if has_error:
        return has_error

    data = await RegisterRepository().register(
        register_data=register_data,
    )
    response = UserRegisterResponse(
        success=True,
        message="User registered successfully.",
        data=UserRegisterOutput(
            **data.to_dict(),
        ),
    )
    return response
