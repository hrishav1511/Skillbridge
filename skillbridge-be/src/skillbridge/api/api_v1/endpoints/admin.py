from uuid import UUID
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, status

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.service import ServiceRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.api.repositories.dashboard import DashboardRepository
from skillbridge.api.repositories.user_role_association import (
    UserRoleAssociationRepository,
)
from skillbridge.api.schemas.service import (
    AdminServiceOutput,
    PaginatedAdminServices,
    ServiceStatusInput,
    ServiceRevisionOutput,
    ApproveServiceRevisionResponse,
    RejectServiceRevisionResponse,
    ListServiceRevisionsResponse,
    RejectServiceRevisionInput,
    ApproveServiceRevisionInput,
)
from skillbridge.api.schemas.tutor import (
    TutorRevisionOutput,
    ApproveTutorRevisionResponse,
    RejectTutorRevisionResponse,
    ListTutorRevisionsResponse,
    RejectTutorRevisionInput,
    PaginatedTutors,
    TutorAccountStatusInput,
    TutorOutput,
)
from skillbridge.api.schemas.user import UserOutput
from skillbridge.api.schemas.dashboard import AdminDashboardResponse
from skillbridge.exceptions import NotFoundError, handle_exceptions

router = APIRouter()


@router.get(
    "/dashboard/",
    status_code=status.HTTP_200_OK,
    response_model=AdminDashboardResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def admin_dashboard(
    request: Request,
    user_id: UUID = None,
):
    await _require_admin(user_id)
    return {
        "success": True,
        "message": "Admin dashboard fetched.",
        "data": await DashboardRepository().get_admin_dashboard(),
    }


@router.get(
    "/tutors/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTutors,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_admin_tutors(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user_id: UUID = None,
):
    await _require_admin(user_id)
    response = await TutorRepository().get_admin_tutors(limit=limit, offset=offset)
    output = []
    for tutor in response["data"]:
        user = tutor.tutor_ura[0].ura_user if tutor.tutor_ura else None
        output.append(
            TutorOutput(
                **tutor.to_dict(),
                account_status=tutor.status,
                user=UserOutput(**user.to_dict()) if user else None,
            )
        )
    response["data"] = output
    return PaginatedTutors(**response)


@router.patch(
    "/tutors/{tutor_id}/status/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def update_tutor_account_status(
    request: Request,
    tutor_id: UUID,
    status_input: TutorAccountStatusInput,
    user_id: UUID = None,
):
    await _require_admin(user_id)
    account_status = status_input.status.strip().upper()
    if account_status not in {"ACTIVE", "INACTIVE"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be ACTIVE or INACTIVE.",
        )
    tutor = await TutorRepository().set_account_status(
        tutor_id=tutor_id,
        account_status=account_status,
    )
    return {
        "success": True,
        "message": f"Tutor account {account_status.lower()}.",
        "data": {"tutor_id": tutor.id, "status": tutor.status},
    }


@router.get(
    "/services/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedAdminServices,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_admin_services(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user_id: UUID = None,
):
    """Every service, disabled ones included, for the moderation list."""
    await _require_admin(user_id)
    response = await ServiceRepository().get_admin_services(limit=limit, offset=offset)
    output = []
    for service in response["data"]:
        tutor = service.service_tutor
        user = tutor.tutor_ura[0].ura_user if tutor and tutor.tutor_ura else None
        output.append(
            AdminServiceOutput(
                **service.to_dict(),
                tutor=UserOutput(**user.to_dict()) if user else None,
                tutor_user_id=user.id if user else None,
            )
        )
    response["data"] = output
    return PaginatedAdminServices(**response)


@router.patch(
    "/services/{service_id}/status/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def update_service_status(
    request: Request,
    service_id: UUID,
    status_input: ServiceStatusInput,
    user_id: UUID = None,
):
    """Disable or re-enable a service.

    Mirrors the tutor account-status action. A disabled service falls out of
    the student listing through the existing ACTIVE filter on public queries.
    """
    await _require_admin(user_id)
    service_status = status_input.status.strip().upper()
    if service_status not in {"ACTIVE", "INACTIVE"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be ACTIVE or INACTIVE.",
        )
    service = await ServiceRepository().set_service_status(
        service_id=service_id,
        service_status=service_status,
    )
    return {
        "success": True,
        "message": f"Service {service_status.lower()}.",
        "data": {"service_id": service.id, "status": service.status},
    }


def _get_user_role(current_user: Dict[str, Any]) -> str:
    """Extract role from JWT token."""
    return current_user.get("role", "").lower()


def _get_user_id(current_user: Dict[str, Any]) -> UUID:
    """Extract user ID from JWT token."""
    return UUID(current_user.get("sub", ""))


def _get_tutor_id(current_user: Dict[str, Any]) -> UUID | None:
    """Extract tutor ID from JWT token if user is a tutor."""
    tutor_id = current_user.get("tutor_id")
    return UUID(tutor_id) if tutor_id else None


async def _require_admin(user_id: UUID):
    """Check if user is admin through the role association table."""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    is_admin = await UserRoleAssociationRepository().is_user_admin(user_id=user_id)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def _require_tutor(current_user: Dict[str, Any]):
    """Check if user is tutor."""
    role = _get_user_role(current_user)
    if role != "tutor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tutor access required.",
        )


@router.get(
    "/service_revisions/pending/",
    status_code=status.HTTP_200_OK,
    response_model=ListServiceRevisionsResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_pending_revisions(
    request: Request,
    user_id: UUID = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get all pending service revisions awaiting admin approval.
    Admin only.
    """
    await _require_admin(user_id)

    response = await ServiceRepository().get_pending_revisions(
        limit=limit,
        offset=offset,
    )

    response["data"] = [ServiceRevisionOutput(**revision) for revision in response.get("data", [])]
    return ListServiceRevisionsResponse(**response)


@router.post(
    "/service_revisions/{service_revision_id}/approve/",
    status_code=status.HTTP_200_OK,
    response_model=ApproveServiceRevisionResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def approve_service_revision(
    request: Request,
    service_revision_id: UUID,
    approve_input: ApproveServiceRevisionInput | None = None,
    user_id: UUID = None,
):
    """
    Approve a pending service revision.
    - For CREATE: Creates the service and makes it visible to students
    - For UPDATE: Updates the published service
    - For DELETE: Deletes the service
    Admin only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    await _require_admin(user_id)

    response = await ServiceRepository().approve_revision(
        revision_id=service_revision_id,
        user_id=user_id,
    )

    return ApproveServiceRevisionResponse(
        success=response["success"],
        message=response["message"],
        data=ServiceRevisionOutput(**response["data"]),
    )


@router.post(
    "/service_revisions/{service_revision_id}/reject/",
    status_code=status.HTTP_200_OK,
    response_model=RejectServiceRevisionResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def reject_service_revision(
    request: Request,
    service_revision_id: UUID,
    reject_input: RejectServiceRevisionInput,
    user_id: UUID = None,
):
    """
    Reject a pending service revision.
    The published service remains unchanged.
    Admin only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    await _require_admin(user_id)

    response = await ServiceRepository().reject_revision(
        revision_id=service_revision_id,
        rejection_reason=reject_input.rejection_reason,
    )

    return RejectServiceRevisionResponse(
        success=response["success"],
        message=response["message"],
        data=ServiceRevisionOutput(**response["data"]),
    )


@router.get(
    "/tutor_revisions/pending/",
    status_code=status.HTTP_200_OK,
    response_model=ListTutorRevisionsResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_pending_tutor_revisions(
    request: Request,
    user_id: UUID = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get all pending tutor revisions awaiting admin approval.
    Admin only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    await _require_admin(user_id)

    response = await TutorRepository().get_pending_tutor_revisions(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    response["data"] = [TutorRevisionOutput(**revision) for revision in response.get("data", [])]
    return ListTutorRevisionsResponse(**response)


@router.post(
    "/tutor_revisions/{tutor_revision_id}/approve/",
    status_code=status.HTTP_200_OK,
    response_model=ApproveTutorRevisionResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def approve_tutor_revision(
    request: Request,
    tutor_revision_id: UUID,
    user_id: UUID = None,
):
    """
    Approve a pending tutor revision.
    Admin only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    await _require_admin(user_id)

    response = await TutorRepository().approve_tutor_revision(
        revision_id=tutor_revision_id,
        user_id=user_id,
    )

    return ApproveTutorRevisionResponse(
        success=response["success"],
        message=response["message"],
        data=TutorRevisionOutput(**response["data"]),
    )


@router.post(
    "/tutor_revisions/{tutor_revision_id}/reject/",
    status_code=status.HTTP_200_OK,
    response_model=RejectTutorRevisionResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def reject_tutor_revision(
    request: Request,
    tutor_revision_id: UUID,
    reject_input: RejectTutorRevisionInput,
    user_id: UUID = None,
):
    """
    Reject a pending tutor revision.
    Admin only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    await _require_admin(user_id)

    response = await TutorRepository().reject_tutor_revision(
        revision_id=tutor_revision_id,
        rejection_reason=reject_input.rejection_reason,
    )

    return RejectTutorRevisionResponse(
        success=response["success"],
        message=response["message"],
        data=TutorRevisionOutput(**response["data"]),
    )
