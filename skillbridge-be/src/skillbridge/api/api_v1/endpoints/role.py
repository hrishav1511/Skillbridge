import cProfile

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from skillbridge.api.repositories.role import RoleRepository
from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.schemas.role import (
    CreateRoleInput,
    CreateRoleOutput,
    CreateRoleResponse,
    PaginatedRoles,
    RoleQueryCriteria,
)
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.role import CreateRoleInputValidator
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRoleResponse,  # validate the function response and strip out the extra fields returned if any
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def create_role(request: Request, role: CreateRoleInput, user_id: UUID = None):
    if not await UserRoleAssociationRepository().is_user_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required.")
    has_error, role = BaseValidator.validate(
        validator=CreateRoleInputValidator,
        input_data=role,
    )

    if has_error:
        return has_error

    data = await RoleRepository().create_role(
        role=role,
    )
    response = CreateRoleResponse(
        success=data["success"],
        message=data["message"],
        data=CreateRoleOutput(
            **data["data"].to_dict(),
        ),
    )
    return response


@router.get(
    "/roles/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedRoles,
    response_model_by_alias=False,
)
@handle_exceptions
async def roles(
    *,
    request: Request,
    query: RoleQueryCriteria = Depends(RoleQueryCriteria),
):
    response = await RoleRepository().get_paginated_results(
        query=query,
    )
    res_data = [
        {**res.to_dict()}
        for res in response.get("data", [])
        if str(res.slug).lower() in {"student", "tutor"}
    ]
    response["metadata"]["total"] = len(res_data)

    response["data"] = res_data

    data = PaginatedRoles(**response)
    # profiler.print_stats(sort="cumulative")
    return data
