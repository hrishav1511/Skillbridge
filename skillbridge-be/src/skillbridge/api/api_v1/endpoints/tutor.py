from uuid import UUID
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.repositories.auth.token import get_optional_user_id, validate_token
from skillbridge.api.api_v1.endpoints.service import _get_tutor_id, _require_tutor
from skillbridge.api.repositories.review import ReviewRepository, format_average_rating
from skillbridge.api.repositories.service import ServiceRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.api.repositories.favorite import FavoriteRepository
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.schemas.service import (
    PaginatedServiceRevisions,
    PaginatedServices,
    ServiceQueryCriteria,
    ServiceRevisionOutput,
    ServiceRevisionQueryCriteria,
)
from skillbridge.api.schemas.tutor import (
    CoverPictureUploadResponse,
    AcademicProgramListResponse,
    TutorTagListResponse,
    CreateTutorInput,
    CreateTutorOutput,
    CreateTutorResponse,
    PaginatedTutorRevisions,
    PaginatedTutors,
    ProfilePictureUploadResponse,
    RejectTutorRevisionInput,
    TutorOutput,
    TutorQueryCriteria,
    TutorRevisionOutput,
    UpdateTutorInput,
    UpdateTutorOutput,
    UpdateTutorRevisionResponse,
    TutorVisibilityInput,
    TutorAvailabilityInput,
    TutorControlOutput,
)
from skillbridge.api.schemas.user import UserOutput
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.tutor import (
    CreateTutorInputValidator,
    UpdateTutorInputValidator,
)
from skillbridge.exceptions import handle_exceptions
from skillbridge.api.services.media_service import MediaService
from skillbridge.database.db.database import get_session
from skillbridge.utils.service_time import get_service_schedule_status

router = APIRouter()


# Helper function
async def get_media_service():
    tutor_repository = TutorRepository()
    return MediaService(tutor_repository)


async def _require_tutor_owner(user_id: UUID, tutor_id: UUID) -> None:
    owned_tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id)
    if owned_tutor_id != tutor_id:
        raise HTTPException(status_code=403, detail="You can modify only your own tutor profile.")


@router.get(
    "/academic-programs/",
    status_code=status.HTTP_200_OK,
    response_model=AcademicProgramListResponse,
    response_model_by_alias=False,
)
@handle_exceptions
async def list_academic_programs(request: Request):
    """Distinct academic programs, for populating the tutor filter dropdown.

    Browsing is open to guests, and this dropdown sits directly above the
    public tutor and service lists. The repository already restricts the
    result to visible, active, approved tutors, so the programs it returns are
    exactly what an anonymous caller can already see in /tutors/ - requiring a
    token here only broke guest browsing.
    """
    # Still authenticate a bearer token when one is sent, so a bad or expired
    # token is reported rather than silently treated as a guest.
    await get_optional_user_id(request)
    programs = await TutorRepository().list_academic_programs()
    return AcademicProgramListResponse(
        success=True,
        message="Academic programs have been fetched.",
        data=programs,
    )


@router.get(
    "/tags/",
    status_code=status.HTTP_200_OK,
    response_model=TutorTagListResponse,
    response_model_by_alias=False,
)
@handle_exceptions
async def list_tutor_tags(request: Request):
    """Distinct subject tags, for the tutor search filter.

    Public for the same reason as /academic-programs/: it sits above the
    public tutor list and exposes nothing a guest cannot already browse.
    """
    await get_optional_user_id(request)
    tags = await TutorRepository().list_tags()
    return TutorTagListResponse(
        success=True,
        message="Tutor tags have been fetched.",
        data=tags,
    )


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateTutorResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def create_tutor(
    request: Request,
    tutor_input: CreateTutorInput,
    user_id: UUID = None,
):
    raise HTTPException(
        status_code=403,
        detail="Tutor profiles must be created through the registration and approval workflow.",
    )


@router.get(
    "/tutors/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTutors,
    response_model_by_alias=False,
)
@handle_exceptions
async def get_tutors(
    *,
    request: Request,
    query: TutorQueryCriteria = Depends(TutorQueryCriteria),
    user_id: UUID = None,
):
    user_id = await get_optional_user_id(request)
    favorite_tutor_ids = set()
    student_id = None
    owned_tutor_id = None
    if user_id is not None:
        student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
        if student_id is not None:
            favorite_tutor_ids = await FavoriteRepository().get_tutor_ids(student_id)
        else:
            owned_tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(
                user_id
            )

    # A tutor asking for their own record is not public browsing: they must
    # still see their own profile while it is hidden, paused, or awaiting
    # approval. The tutor_id filter keeps the result to that single row, so
    # this cannot be used to enumerate profiles hidden from the marketplace.
    query.public_only = not (
        owned_tutor_id is not None
        and query.tutor_id is not None
        and query.tutor_id == owned_tutor_id
    )
    if query.favorite_only and student_id is None:
        raise HTTPException(status_code=403, detail="Student access required for favorites.")
    tutors = await TutorRepository().get_paginated_results(query=query)
    res_data = []
    for tutor in tutors["data"]:
        user = tutor.tutor_ura[0].ura_user if tutor.tutor_ura else None
        # The tutor's own "my profile" page reads user.email/user.phone. Those
        # were never populated on this response, so the icons rendered blank
        # even for the owner. Everyone else keeps seeing nothing here, same as
        # before - the account's email/phone stay private to its owner.
        is_owner_view = owned_tutor_id is not None and tutor.id == owned_tutor_id
        average_rating = await ReviewRepository().get_tutor_average_rating(tutor_id=tutor.id)
        res_data.append(
            TutorOutput(
                **{
                    **tutor.to_dict(),
                    # A tutor's contact number is protected profile data. Guests
                    # may browse the marketplace, but must authenticate before
                    # receiving it.
                    "phone": tutor.phone if user_id is not None else None,
                    "is_favorite": tutor.id in favorite_tutor_ids,
                    "average_rating": format_average_rating(average_rating),
                    "user": (
                        UserOutput(
                            full_name=user.full_name,
                            id=user.id if user_id is not None else None,
                            email=user.email if is_owner_view else None,
                            phone=user.phone if is_owner_view else None,
                        )
                        if user
                        else None
                    ),
                }
            )
        )
    if query.favorite_only:
        res_data = [item for item in res_data if item.is_favorite]
        tutors["metadata"]["total"] = len(res_data)
    res_data.sort(key=lambda item: item.is_favorite, reverse=True)
    tutors["data"] = res_data
    response = PaginatedTutors(**tutors)
    return response


@router.get("/filter-options/", status_code=status.HTTP_200_OK)
@handle_exceptions
async def tutor_filter_options():
    return await TutorRepository().get_filter_options()


@router.patch(
    "/me/visibility/",
    response_model=TutorControlOutput,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def update_my_tutor_visibility(
    request: Request,
    payload: TutorVisibilityInput,
    user_id: UUID = None,
):
    tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id)
    if tutor_id is None:
        raise HTTPException(status_code=403, detail="Tutor access required.")
    tutor = await TutorRepository().update_visibility(tutor_id, user_id, payload.is_visible)
    return TutorControlOutput(
        tutor_id=tutor.id,
        is_visible=tutor.is_visible,
        accepting_requests=tutor.accepting_requests,
    )


@router.patch(
    "/me/availability/",
    response_model=TutorControlOutput,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def update_my_tutor_availability(
    request: Request,
    payload: TutorAvailabilityInput,
    user_id: UUID = None,
):
    tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id)
    if tutor_id is None:
        raise HTTPException(status_code=403, detail="Tutor access required.")
    tutor = await TutorRepository().update_availability(
        tutor_id, user_id, payload.accepting_requests
    )
    return TutorControlOutput(
        tutor_id=tutor.id,
        is_visible=tutor.is_visible,
        accepting_requests=tutor.accepting_requests,
    )


@router.put(
    "/{tutor_id}/",
    status_code=status.HTTP_200_OK,
    # The update is staged as a revision for admin approval, so the handler
    # returns the revision. Declaring the plain tutor response here silently
    # dropped the revision-only fields (revision_type, moderation_*) from the
    # body the client actually received.
    response_model=UpdateTutorRevisionResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def update_tutor(
    request: Request,
    tutor_id: UUID,
    tutor_input: UpdateTutorInput,
    user_id: UUID = None,
):
    await _require_tutor_owner(user_id, tutor_id)
    has_error, tutor_input = BaseValidator.validate(
        validator=UpdateTutorInputValidator,
        input_data=tutor_input,
    )

    if has_error:
        return has_error

    revision = await TutorRepository().update_tutor(
        tutor_id=tutor_id,
        update_data=tutor_input,
    )

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tutor not found."
        )

    # Return the revision record as a pending update
    response_data = {
        **revision["data"].to_dict(),
        "user": None,
    }
    if revision["data"].tutor_revision_tutor and revision["data"].tutor_revision_tutor.tutor_ura:
        user = revision["data"].tutor_revision_tutor.tutor_ura[0].ura_user
        response_data["user"] = UserOutput(**user.to_dict()) if user else None

    return UpdateTutorRevisionResponse(
        success=True,
        message="Tutor profile update submitted for admin approval.",
        data=TutorRevisionOutput(**response_data),
    )


@router.post(
    "/{tutor_id}/upload-profile-picture/",
    response_model=ProfilePictureUploadResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def upload_profile_picture(
    request: Request,
    tutor_id: UUID,
    file: UploadFile = File(...),
    media_service: MediaService = Depends(get_media_service),
    user_id: UUID = None,
):
    """Upload profile picture for a tutor"""
    await _require_tutor_owner(user_id, tutor_id)
    profile_url = await media_service.upload_profile_picture(tutor_id, file)

    return ProfilePictureUploadResponse(
        profile_picture_url=profile_url, message="Profile picture uploaded successfully"
    )


@router.post(
    "/{tutor_id}/upload-cover-picture/",
    response_model=CoverPictureUploadResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def upload_cover_picture(
    request: Request,
    tutor_id: UUID,
    file: UploadFile = File(...),
    media_service: MediaService = Depends(get_media_service),
    user_id: UUID = None,
):
    """Upload cover picture for a tutor"""
    await _require_tutor_owner(user_id, tutor_id)
    cover_url = await media_service.upload_cover_picture(tutor_id, file)

    return CoverPictureUploadResponse(
        cover_picture_url=cover_url, message="Cover picture uploaded successfully"
    )


@router.delete("/{tutor_id}/profile-picture/", status_code=status.HTTP_200_OK)
@handle_exceptions
@validate_token
async def delete_profile_picture(
    request: Request,
    tutor_id: UUID,
    user_id: UUID = None,
    media_service: MediaService = Depends(get_media_service),
):
    """Delete profile picture"""
    await _require_tutor_owner(user_id, tutor_id)
    await media_service.delete_profile_picture(tutor_id)
    return {"message": "Profile picture deleted successfully"}


@router.delete("/{tutor_id}/cover-picture/", status_code=status.HTTP_200_OK)
@handle_exceptions
@validate_token
async def delete_cover_picture(
    request: Request,
    tutor_id: UUID,
    user_id: UUID = None,
    media_service: MediaService = Depends(get_media_service),
):
    """Delete cover picture"""
    await _require_tutor_owner(user_id, tutor_id)
    await media_service.delete_cover_picture(tutor_id)
    return {"message": "Cover picture deleted successfully"}






@router.get(
    "/my-services/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedServices,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def get_my_services(
    request: Request,
    user_id: UUID = None,
    query: ServiceQueryCriteria = Depends(ServiceQueryCriteria),
):
    """
    Get all published services by the authenticated tutor.
    Tutor only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    tutor_association = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id=user_id)
    if tutor_association is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tutor access required.")
    response = await ServiceRepository().get_tutor_services(
        tutor_id=tutor_association,
        approval_status=getattr(query, "approval_status", None),
        limit=query.items_per_page,
        offset=(query.page - 1) * query.items_per_page,
    )
    
    res_data = []
    for service in response.get("data", []):
        tutor = (
            service.service_tutor.tutor_ura[0].ura_user
            if service.service_tutor and service.service_tutor.tutor_ura
            else None
        )
        res_data.append(
            {
                **service.to_dict(),
                "schedule_status": get_service_schedule_status(
                    service.date, service.time, service.end_time
                ),
                "tutor": tutor and {
                    "full_name": tutor.full_name,
                    "email": tutor.email,
                    "id": tutor.id,
                },
            }
        )
    
    response["data"] = res_data
    return PaginatedServices(**response)


@router.get(
    "/my-service_revisions/",
    status_code=status.HTTP_200_OK,
    response_model= PaginatedServiceRevisions,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def get_my_service_revisions(
    request: Request,
    user_id: UUID = None,
    query: ServiceRevisionQueryCriteria = Depends(ServiceRevisionQueryCriteria),
):
    """
    Get all revisions (pending, approved, rejected) created by the authenticated tutor.
    Tutor only.
    The user_id is extracted from JWT token via @validate_token decorator.
    """
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    tutor_association = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id=user_id)
    if tutor_association is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tutor access required.")

    response = await ServiceRepository().get_tutor_revisions(
        tutor_id=tutor_association,
        approval_status=query.approval_status,
        limit=query.items_per_page,
        offset=(query.page - 1) * query.items_per_page,
    )
    
    res_data = []
    for service_revision in response.get("data", []):
        tutor = (
            service_revision.service_revision_tutor.tutor_ura[0].ura_user
            if service_revision.service_revision_tutor and service_revision.service_revision_tutor.tutor_ura
            else None
        )
        res_data.append(
            ServiceRevisionOutput(
                **{
                    **service_revision.to_dict(),
                    "tutor": tutor and {
                        "full_name": tutor.full_name,
                        "email": tutor.email,
                        "id": tutor.id,
                    },
                }
            )
        )
    
    response["data"] = res_data
    return PaginatedServiceRevisions(**response)


@router.get(
    "/my-tutor_revisions/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTutorRevisions,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def get_my_tutor_revisions(
    request: Request,
    tutor_id: UUID,
    query: TutorQueryCriteria = Depends(TutorQueryCriteria),
    user_id: UUID = None,
):
    """
    Get tutor revisions (pending, approved, rejected) created by the authenticated tutor.
    Tutor only.
    """
    await _require_tutor_owner(user_id, tutor_id)
    response = await TutorRepository().get_tutor_revisions(
        tutor_id=tutor_id,
        approval_status=query.approval_status,
        limit=query.items_per_page,
        offset=(query.page - 1) * query.items_per_page,
    )

    res_data = []
    for tutor_revision in response.get("data", []):
        user = (
            tutor_revision.tutor_revision_tutor.tutor_ura[0].ura_user
            if tutor_revision.tutor_revision_tutor and tutor_revision.tutor_revision_tutor.tutor_ura
            else None
        )
        res_data.append(
            TutorRevisionOutput(
                **{
                    **tutor_revision.to_dict(),
                    "user": user and {
                        "full_name": user.full_name,
                        "email": user.email,
                        "id": user.id,
                    },
                }
            )
        )

    response["data"] = res_data
    return PaginatedTutorRevisions(**response)
