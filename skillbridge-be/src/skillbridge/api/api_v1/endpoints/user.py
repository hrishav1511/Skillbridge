from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from skillbridge.api.repositories.user import UserRepository
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.schemas.user import (
    DeleteUserOutput,
    DeleteUserResponse,
    GETPendingSocketRequestsResponse,
    GetUserOutput,
    GetUserResponse,
    PaginatedUsers,
    UpdateUserInput,
    UpdateUserOutput,
    UpdateUserResponse,
    UserOutput,
    UserQueryCriteria,
)

from skillbridge.api.validators.base import BaseValidator
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


@router.get(
    "/users/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedUsers,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def get_users(
    request: Request,
    query: UserQueryCriteria = Depends(UserQueryCriteria),
    user_id: UUID = None,
):
    if not await UserRoleAssociationRepository().is_user_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required.")
    response = await UserRepository().get_paginated_results(query=query)

    res_data = [{**res.to_dict()} for res in response.get("data", [])]

    response["data"] = res_data
    response = PaginatedUsers(
        **response,
    )
    return response
