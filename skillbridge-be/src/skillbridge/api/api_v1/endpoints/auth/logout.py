from fastapi import APIRouter, Request

from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.api.repositories.auth.token import validate_token

from skillbridge.api.schemas.token import LogoutRequest
router = APIRouter()




@router.post("/logout/")
@validate_token
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    user_id=None,
):
    """
    Logout by revoking refresh token.
    """
    await TokenRepository().logout(logout_data.refresh_token, user_id=user_id)
    return {"success": True, "message": "Logged out successfully."}
