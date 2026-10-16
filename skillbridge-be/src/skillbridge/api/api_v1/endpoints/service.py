import json
from datetime import date as DateType, time as TimeType
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from skillbridge.api.repositories.auth.token import get_optional_user_id, validate_token
from skillbridge.api.repositories.review import ReviewRepository, format_average_rating
from skillbridge.api.repositories.service import ServiceRepository
from skillbridge.api.repositories.favorite import FavoriteRepository
from skillbridge.api.repositories.service_attachment import ServiceAttachmentRepository
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.services.media_service import MediaService
from skillbridge.api.core.s3_client import s3_client
from skillbridge.api.core.s3_client import s3_client
from skillbridge.api.schemas.service import (
    CreateServiceOutput,
    CreateServiceResponse,
    DeleteServiceResponse,
    GetServiceOutput,
    GetServiceResponse,
    PaginatedServices,
    ServiceQueryCriteria,
    ServiceRevisionQueryCriteria,
    UpdateServiceOutput,
    UpdateServiceResponse,
    ServiceRevisionOutput,
    ApproveServiceRevisionResponse,
    RejectServiceRevisionResponse,
    ListServiceRevisionsResponse,
    PaginatedServiceRevisions,
    RejectServiceRevisionInput,
)
from skillbridge.api.schemas.service_attachment import (
    ServiceAttachmentDeleteOutput,
    ServiceAttachmentDeleteResponse,
    ServiceAttachmentListResponse,
    ServiceAttachmentOutput,
    ServiceAttachmentResponse,
)
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.service import (
    CreateServiceInputValidator,
    UpdateServiceInputValidator,
)
from skillbridge.exceptions import NotFoundError, handle_exceptions
from skillbridge.utils.service_time import get_service_schedule_status

router = APIRouter()


def _parse_existing_urls(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(url) for url in parsed if url]
    except json.JSONDecodeError:
        pass
    return [url.strip() for url in value.split(",") if url.strip()]


def _normalise_level(value: str | None) -> str | None:
    """Accept the level in any case; the enum itself stays upper-case.

    An empty form field becomes None so the validator reports it as missing
    rather than as an unparseable enum value.
    """
    if not isinstance(value, str):
        return value
    normalised = value.strip().upper()
    return normalised or None


def _parse_tags(value: str | None) -> list[str] | None:
    if value is None:
        return None
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(tag) for tag in parsed if str(tag).strip()]
    except json.JSONDecodeError:
        pass
    return [tag.strip() for tag in value.split(",") if tag.strip()]


async def _upload_service_media(
    tutor_id: UUID,
    images: list[UploadFile] | None = None,
    videos: list[UploadFile] | None = None,
    existing_image_urls: str | None = None,
    existing_video_urls: str | None = None,
) -> tuple[list[str], list[str]]:
    media_service = MediaService()
    image_urls = _parse_existing_urls(existing_image_urls)
    video_urls = _parse_existing_urls(existing_video_urls)

    for image in images or []:
        if image and image.filename:
            image_urls.append(await media_service.upload_service_image(tutor_id, image))

    for video in videos or []:
        if video and video.filename:
            video_urls.append(await media_service.upload_service_video(tutor_id, video))

    return image_urls, video_urls


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


def _require_admin(current_user: Dict[str, Any]):
    """Check if user is admin."""
    role = _get_user_role(current_user)
    if role not in ("admin", "super_admin"):
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


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateServiceResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def create_service(
    request: Request,
    tutor_id: UUID = Form(...),
    service_name: str = Form(...),
    description: str | None = Form(None),
    date: DateType = Form(...),
    time: TimeType = Form(...),
    end_time: TimeType = Form(...),
    price: int = Form(...),
    level: str = Form(...),
    joining_link: str | None = Form(None),
    tags: str | None = Form(None),
    images: list[UploadFile] | None = File(None),
    videos: list[UploadFile] | None = File(None),
    video: UploadFile | None = File(None),
    user_id: UUID = None,
):
    """
    Create a new service. Creates a PENDING revision for admin approval.
    Only tutors can create services.
    The user_id is extracted from the JWT token via validate_token decorator.
    """
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    associated_tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id=user_id)
    if associated_tutor_id is None or associated_tutor_id != tutor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tutors can only create services for themselves.",
        )
    
    if images and len(images) > MediaService.MAX_SERVICE_IMAGES:
        raise HTTPException(
            status_code=422,
            detail=f"A maximum of {MediaService.MAX_SERVICE_IMAGES} service images is allowed.",
        )
    upload_videos = list(videos or [])
    if video and video.filename and not upload_videos:
        upload_videos.append(video)
    if len(upload_videos) > MediaService.MAX_SERVICE_VIDEOS:
        raise HTTPException(
            status_code=422,
            detail=f"A maximum of {MediaService.MAX_SERVICE_VIDEOS} service videos is allowed.",
        )

    has_error, valid_input = BaseValidator.validate(
        validator=CreateServiceInputValidator,
        tutor_id=tutor_id,
        service_name=service_name,
        description=description,
        date=date,
        time=time,
        end_time=end_time,
        price=price,
        level=_normalise_level(level),
        joining_link=joining_link,
        tags=_parse_tags(tags),
    )
    if has_error:
        return has_error

    image_urls, video_urls = await _upload_service_media(
        tutor_id=tutor_id,
        images=images,
        videos=upload_videos,
    )
    video_url = video_urls[0] if video_urls else None

    valid_input = valid_input.model_copy(
        update={"image_urls": image_urls, "video_url": video_url, "video_urls": video_urls}
    )
    try:
        data = await ServiceRepository().create_service(service_input=valid_input)
    except Exception:
        for media_url in [*image_urls, *video_urls]:
            s3_client.delete_file(media_url)
        raise
    return CreateServiceResponse(
        success=data["success"],
        message=data["message"],
        data=CreateServiceOutput(**data["data"].to_dict()),
    )


@router.get(
    "/services/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedServices,
    response_model_by_alias=False,
)
@handle_exceptions
async def get_services(
    request: Request,
    query: ServiceQueryCriteria = Depends(ServiceQueryCriteria),
    user_id: UUID = None,
):
    """
    Get all approved/published services. Visible to all users (students can discover services).
    """
    user_id = await get_optional_user_id(request)
    favorite_service_ids = set()
    student_id = None
    owned_tutor_id = None
    if user_id is not None:
        student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
        if student_id is not None:
            favorite_service_ids = await FavoriteRepository().get_service_ids(student_id)
        else:
            owned_tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(
                user_id
            )

    # A tutor listing their own services is not public browsing: hiding their
    # profile or pausing requests must not hide their services from them. The
    # tutor_id filter keeps the result to their own rows.
    query.public_only = not (
        owned_tutor_id is not None
        and query.tutor_id is not None
        and query.tutor_id == owned_tutor_id
    )
    response = await ServiceRepository().get_paginated_results(query=query)
    if query.favorite_only and student_id is None:
        raise HTTPException(status_code=403, detail="Student access required for favorites.")
    enrolment_counts = await ServiceRepository().get_accepted_booking_counts(
        [service.id for service in response.get("data", [])]
    )
    res_data = []
    for service in response.get("data", []):
        tutor = (
            service.service_tutor.tutor_ura[0].ura_user
            if service.service_tutor and service.service_tutor.tutor_ura
            else None
        )
        average_rating = await ReviewRepository().get_service_average_rating(service_id=service.id)
        res_data.append(
            {
                **service.to_dict(),
                "is_favorite": service.id in favorite_service_ids,
                "enrolled_students_count": enrolment_counts.get(service.id, 0),
                "schedule_status": get_service_schedule_status(
                    service.date, service.time, service.end_time
                ),
                "average_rating": format_average_rating(average_rating),
                "tutor": tutor and (
                    {
                        "full_name": tutor.full_name,
                        "id": tutor.id,
                    }
                    if user_id is not None
                    else {"full_name": tutor.full_name}
                ),
                "tutor_user_id": tutor.id if (tutor and user_id is not None) else None,
            }
        )
    if query.favorite_only:
        res_data = [item for item in res_data if item["is_favorite"]]
        response["metadata"]["total"] = len(res_data)
    res_data.sort(key=lambda item: item["is_favorite"], reverse=True)
    response["data"] = res_data
    return PaginatedServices(**response)


async def _attachment_output(attachment) -> ServiceAttachmentOutput:
    download_url = s3_client.generate_presigned_download_url(attachment.object_key)
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is temporarily unavailable.",
        )
    return ServiceAttachmentOutput(
        **attachment.to_dict(),
        download_url=download_url,
    )


@router.post(
    "/{service_id}/attachments/",
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceAttachmentResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def upload_service_attachment(
    request: Request,
    service_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    attachment_repository = ServiceAttachmentRepository()
    service = await attachment_repository.get_owned_service(
        service_id=service_id,
        user_id=user_id,
    )
    if service is None:
        raise HTTPException(
            status_code=403,
            detail="Only the service tutor can upload attachments.",
        )

    media_service = MediaService()
    object_key, file_size = await media_service.upload_service_attachment(
        service.tutor_id, file
    )
    try:
        attachment = await attachment_repository.create(
            service_id=service_id,
            tutor_id=service.tutor_id,
            original_filename=file.filename,
            content_type=file.content_type,
            file_size=file_size,
            object_key=object_key,
        )
    except Exception:
        s3_client.delete_key(object_key)
        raise

    return ServiceAttachmentResponse(
        success=True,
        message="Service attachment uploaded.",
        data=await _attachment_output(attachment),
    )


@router.get(
    "/{service_id}/attachments/",
    status_code=status.HTTP_200_OK,
    response_model=ServiceAttachmentListResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_service_attachments(
    request: Request,
    service_id: UUID,
    user_id: UUID = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    attachments = await ServiceAttachmentRepository().list_for_service(
        service_id=service_id,
        user_id=user_id,
    )
    if attachments is None:
        raise HTTPException(status_code=403, detail="Service access required.")
    return ServiceAttachmentListResponse(
        success=True,
        message="Service attachments fetched.",
        data=[await _attachment_output(item) for item in attachments],
    )


@router.get(
    "/attachments/{attachment_id}/download/",
    status_code=status.HTTP_200_OK,
    response_model=ServiceAttachmentResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def get_service_attachment_download(
    request: Request,
    attachment_id: UUID,
    user_id: UUID = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    attachment = await ServiceAttachmentRepository().get_for_user(
        attachment_id=attachment_id,
        user_id=user_id,
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return ServiceAttachmentResponse(
        success=True,
        message="Attachment download URL generated.",
        data=await _attachment_output(attachment),
    )


@router.delete(
    "/attachments/{attachment_id}/",
    status_code=status.HTTP_200_OK,
    response_model=ServiceAttachmentDeleteResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def delete_service_attachment(
    request: Request,
    attachment_id: UUID,
    user_id: UUID = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    attachment = await ServiceAttachmentRepository().delete_for_tutor(
        attachment_id=attachment_id,
        user_id=user_id,
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    if not s3_client.delete_key(attachment.object_key):
        raise HTTPException(
            status_code=503,
            detail="Attachment metadata deleted, but file cleanup failed.",
        )
    return ServiceAttachmentDeleteResponse(
        success=True,
        message="Service attachment deleted.",
        data=ServiceAttachmentDeleteOutput(id=attachment.id, deleted=True),
    )


@router.get(
    "/{service_id}/",
    status_code=status.HTTP_200_OK,
    response_model=GetServiceResponse,
    response_model_by_alias=False,
)
@handle_exceptions
async def get_service(request: Request, service_id: UUID, user_id: UUID = None):
    """
    Get a specific approved/published service. Visible to all users.
    """
    user_id = await get_optional_user_id(request)
    query = ServiceQueryCriteria(service_id=service_id, public_only=True, page=1, items_per_page=1)
    response = await ServiceRepository().get_paginated_results(query=query)
    if not response.get("data"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")
    response["data"] = response["data"][0]

    tutor = response["data"].service_tutor
    tutor_data = None
    if tutor and tutor.tutor_ura:
        user = tutor.tutor_ura[0].ura_user
        tutor_data = (
            {
                "full_name": user.full_name,
                "id": user.id,
            }
            if user_id is not None
            else {"full_name": user.full_name}
        )

    average_rating = await ReviewRepository().get_service_average_rating(service_id=service_id)

    return GetServiceResponse(
        success=response["success"],
        message=response["message"],
        data=GetServiceOutput(
            **{
                **response["data"].to_dict(),
                "schedule_status": get_service_schedule_status(
                    response["data"].date,
                    response["data"].time,
                    response["data"].end_time,
                ),
                "average_rating": format_average_rating(average_rating),
                "tutor": tutor_data,
            }
        ),
    )


@router.put(
    "/{service_id}/",
    status_code=status.HTTP_200_OK,
    response_model=UpdateServiceResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def update_service(
    request: Request,
    service_id: UUID,
    tutor_id: UUID = Form(...),
    service_name: str | None = Form(None),
    description: str | None = Form(None),
    date: DateType | None = Form(None),
    time: TimeType | None = Form(None),
    end_time: TimeType | None = Form(None),
    price: int | None = Form(None),
    level: str | None = Form(None),
    joining_link: str | None = Form(None),
    tags: str | None = Form(None),
    existing_image_urls: str | None = Form(None),
    existing_video_urls: str | None = Form(None),
    existing_video_url: str | None = Form(None),
    images: list[UploadFile] | None = File(None),
    videos: list[UploadFile] | None = File(None),
    video: UploadFile | None = File(None),
    user_id: UUID = None,
):
    """
    Update a service. Creates a PENDING revision for admin approval.
    Tutors can only update their own services.
    The user_id is extracted from the JWT token via validate_token decorator.
    """
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    associated_tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id=user_id)
    if associated_tutor_id is None or associated_tutor_id != tutor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tutors can only update their own services.",
        )
    
    existing_videos = existing_video_urls
    if existing_videos is None and existing_video_url:
        existing_videos = json.dumps([existing_video_url])

    upload_videos = list(videos or [])
    if video and video.filename:
        upload_videos.append(video)

    existing_images_list = _parse_existing_urls(existing_image_urls)
    existing_videos_list = _parse_existing_urls(existing_videos)
    if len(existing_images_list) + len(images or []) > MediaService.MAX_SERVICE_IMAGES:
        raise HTTPException(
            status_code=422,
            detail=f"A maximum of {MediaService.MAX_SERVICE_IMAGES} service images is allowed.",
        )
    if len(existing_videos_list) + len(upload_videos) > MediaService.MAX_SERVICE_VIDEOS:
        raise HTTPException(
            status_code=422,
            detail=f"A maximum of {MediaService.MAX_SERVICE_VIDEOS} service videos is allowed.",
        )
    has_error, valid_input = BaseValidator.validate(
        validator=UpdateServiceInputValidator,
        service_name=service_name,
        description=description,
        date=date,
        time=time,
        end_time=end_time,
        price=price,
        level=_normalise_level(level),
        joining_link=joining_link,
        image_urls=existing_images_list,
        video_url=existing_videos_list[0] if existing_videos_list else None,
        video_urls=existing_videos_list,
        tags=_parse_tags(tags),
    )
    if has_error:
        return has_error

    image_urls, video_urls = await _upload_service_media(
        tutor_id=tutor_id,
        images=images,
        videos=upload_videos,
        existing_image_urls=existing_image_urls,
        existing_video_urls=existing_videos,
    )
    video_url = video_urls[0] if video_urls else None
    valid_input = valid_input.model_copy(
        update={"image_urls": image_urls, "video_url": video_url, "video_urls": video_urls}
    )
    newly_uploaded_urls = [
        *image_urls[len(existing_images_list):],
        *video_urls[len(existing_videos_list):],
    ]
    try:
        updated = await ServiceRepository().update_service(
            service_id=service_id,
            update_data=valid_input,
            tutor_id=tutor_id,
        )
    except Exception:
        for media_url in newly_uploaded_urls:
            s3_client.delete_file(media_url)
        raise
    return UpdateServiceResponse(
        success=updated["success"],
        message=updated["message"],
        data=UpdateServiceOutput(**updated["data"].to_dict()),
    )


@router.delete(
    "/{service_id}/",
    status_code=status.HTTP_200_OK,
    response_model=DeleteServiceResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def delete_service(
    request: Request,
    service_id: UUID,
    tutor_id: UUID,
    user_id: UUID = None,
):
    """
    Delete a service. Creates a DELETE revision for admin approval.
    Tutors can only delete their own services.
    The user_id is extracted from the JWT token via validate_token decorator.
    """
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    associated_tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id=user_id)
    if associated_tutor_id is None or associated_tutor_id != tutor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tutors can only delete their own services.",
        )

    deleted = await ServiceRepository().delete_service(
        service_id=service_id,
        tutor_id=tutor_id,
    )
    return DeleteServiceResponse(
        success=deleted["success"],
        message=deleted["message"],
        data=deleted["data"].to_dict() if deleted.get("data") else None,
    )
