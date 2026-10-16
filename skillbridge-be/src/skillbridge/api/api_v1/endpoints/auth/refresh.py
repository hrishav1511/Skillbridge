from fastapi import APIRouter

from skillbridge.api.repositories.auth.token import TokenRepository

from skillbridge.api.schemas.token import  RefreshTokenRequestInput, TokenResponse
from skillbridge.api.validators.base import BaseValidator
from skillbridge.exceptions import handle_exceptions
router = APIRouter()


@router.post("/", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequestInput,
):
    """
    Refresh access token using refresh token.
    """
    return await TokenRepository().refresh_access_token(
        refresh_data.refresh_token,
    )
