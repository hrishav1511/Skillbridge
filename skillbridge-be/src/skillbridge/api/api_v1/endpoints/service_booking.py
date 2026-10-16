from skillbridge.api.validators.service import ServiceScheduleStatus
import json
from datetime import date as DateType, datetime, time as TimeType, timezone
from skillbridge.utils.service_time import (
    get_scheduled_status,
    service_datetime,
)
from typing import Dict, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.service_booking import ServiceBookingRepository
from skillbridge.api.repositories.user_role_association import (
    UserRoleAssociationRepository,
)
from skillbridge.api.schemas.service_booking import (
    CancelBookingInput,
    PaginatedServiceBookings,
    RescheduleHistoryResponse,
    RescheduleProposalInput,
    RescheduleProposalOutput,
    ServiceBookingOutput,
    ServiceBookingQueryCriteria,
)
from skillbridge.api.services.media_service import MediaService
from skillbridge.api.schemas.service import (
    CreateServiceBookingInput,
    CreateServiceBookingOutput,
    CreateServiceBookingResponse,
)
from skillbridge.api.schemas.service import ServiceOutput
from skillbridge.api.schemas.student import StudentOutput
from skillbridge.api.schemas.tutor import TutorOutput
from skillbridge.api.schemas.user import UserOutput
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.service import (
    CreateServiceBookingInputValidator,
)
from skillbridge.exceptions import NotFoundError, handle_exceptions


def get_booking_status(
    service_date: DateType,
    service_time: TimeType,
    service_end_time: TimeType | None = None,
) -> str:
    service_end = service_datetime(
        service_date,
        service_end_time or service_time,
    )
    return "Completed" if service_end <= datetime.now(timezone.utc) else "Upcoming"


router = APIRouter()


@router.delete(
    "/{booking_id}/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def cancel_service_booking(
    request: Request,
    booking_id: UUID,
    payload: CancelBookingInput | None = None,
    user_id: UUID = None,
):
    return await ServiceBookingRepository().cancel_service_booking(
        booking_id=booking_id,
        user_id=user_id,
        reason=payload.reason if payload else None,
    )


@router.patch("/{booking_id}/accept/", status_code=status.HTTP_200_OK)
@handle_exceptions
@validate_token
async def accept_service_booking(
    request: Request, booking_id: UUID, user_id: UUID = None
):
    result = await ServiceBookingRepository().accept_booking(booking_id, user_id)
    return {
        "success": result["success"],
        "message": result["message"],
        "data": {"booking_id": booking_id, "status": result["data"].status},
    }


@router.patch("/{booking_id}/decline/", status_code=status.HTTP_200_OK)
@handle_exceptions
@validate_token
async def decline_service_booking(
    request: Request, booking_id: UUID, user_id: UUID = None
):
    result = await ServiceBookingRepository().decline_booking(booking_id, user_id)
    return {
        "success": result["success"],
        "message": result["message"],
        "data": {"booking_id": booking_id, "status": result["data"].status},
    }


@router.post("/{booking_id}/reschedule/", status_code=status.HTTP_201_CREATED)
@handle_exceptions
@validate_token
async def propose_reschedule(
    request: Request,
    booking_id: UUID,
    payload: RescheduleProposalInput,
    user_id: UUID = None,
):
    proposal = await ServiceBookingRepository().propose_reschedule(
        booking_id, user_id, payload.proposed_start_at
    )
    return {
        "success": True,
        "message": "Reschedule proposal created.",
        "data": RescheduleProposalOutput.model_validate(proposal, from_attributes=True),
    }


@router.patch(
    "/{booking_id}/reschedule/{proposal_id}/accept/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def accept_reschedule(
    request: Request,
    booking_id: UUID,
    proposal_id: UUID,
    user_id: UUID = None,
):
    proposal = await ServiceBookingRepository().respond_to_reschedule(
        booking_id, proposal_id, user_id, accept=True
    )
    return {
        "success": True,
        "message": "Reschedule proposal accepted.",
        "data": RescheduleProposalOutput.model_validate(proposal, from_attributes=True),
    }


@router.patch(
    "/{booking_id}/reschedule/{proposal_id}/reject/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def reject_reschedule(
    request: Request,
    booking_id: UUID,
    proposal_id: UUID,
    user_id: UUID = None,
):
    proposal = await ServiceBookingRepository().respond_to_reschedule(
        booking_id, proposal_id, user_id, accept=False
    )
    return {
        "success": True,
        "message": "Reschedule proposal rejected.",
        "data": RescheduleProposalOutput.model_validate(proposal, from_attributes=True),
    }


@router.get(
    "/{booking_id}/reschedule/",
    response_model=RescheduleHistoryResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def get_reschedule_history(
    request: Request, booking_id: UUID, user_id: UUID = None
):
    proposals = await ServiceBookingRepository().list_reschedule_history(
        booking_id, user_id
    )
    return RescheduleHistoryResponse(
        success=True,
        message="Reschedule history fetched.",
        data=[
            RescheduleProposalOutput.model_validate(item, from_attributes=True)
            for item in proposals
        ],
    )


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
    response_model=CreateServiceBookingResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def create_service_booking(
    request: Request,
    service_booking_input: CreateServiceBookingInput,
    user_id: UUID = None,
):
    """
    Only students can book services.
    The user_id is extracted from JWT token via @validate_token decorator.
    """

    student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(
        user_id
    )
    if student_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student access required."
        )
    if (
        service_booking_input.student_id is not None
        and service_booking_input.student_id != student_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only book services for themselves.",
        )

    # student_id is server-derived, so it is passed as an extra field rather
    # than through the request body model.
    has_error, valid_input = BaseValidator.validate(
        validator=CreateServiceBookingInputValidator,
        service_id=service_booking_input.service_id,
        student_id=student_id,
    )
    if has_error:
        return has_error

    data = await ServiceBookingRepository().create_service_booking(
        service_booking_input=valid_input,
    )
    return CreateServiceBookingResponse(
        success=data["success"],
        message=data["message"],
        data=CreateServiceBookingOutput(**data["data"].to_dict()),
    )


@router.get(
    "/service-bookings/",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedServiceBookings,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def get_service_bookings(
    request: Request,
    service_booking_query: ServiceBookingQueryCriteria = Depends(
        ServiceBookingQueryCriteria
    ),
    user_id: UUID = None,
):
    """
    List service bookings based on query criteria.
    """
    student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(
        user_id
    )
    tutor_id = await UserRoleAssociationRepository().get_tutor_id_by_user_id(user_id)
    is_admin = await UserRoleAssociationRepository().is_user_admin(user_id)
    if student_id is not None:
        service_booking_query.student_id = student_id
        service_booking_query.tutor_id = None
    elif tutor_id is not None:
        service_booking_query.tutor_id = tutor_id
        service_booking_query.student_id = None
    elif not is_admin:
        raise HTTPException(status_code=403, detail="Booking access is restricted.")
    data = await ServiceBookingRepository().get_paginated_results(
        query=service_booking_query,
    )
    booking_outputs = []
    for item in data["data"]:
        booking_payload = item.to_dict()
        service_for_status = getattr(item, "service_booking_service", None)
        if service_for_status:
            booking_payload["booking_status"] = item.status
        service_data = None
        student_data = None
        tutor_data = None

        if getattr(item, "service_booking_service", None):
            service = item.service_booking_service
            service_payload = service.to_dict()
            if item.status != "ACCEPTED":
                service_payload["joining_link"] = None
            service_payload["schedule_status"] = get_scheduled_status(
                item.scheduled_start_at, service.time, service.end_time
            )

            # A service that has finished cannot be joined. Hiding the button
            # is not enough on its own - the link is in the payload, so it is
            # withheld here as well.
            if service_payload["schedule_status"] == ServiceScheduleStatus.COMPLETED:
                service_payload["joining_link"] = None
            tutor = None
            if (
                getattr(service, "service_tutor", None)
                and service.service_tutor.tutor_ura
            ):
                user = service.service_tutor.tutor_ura[0].ura_user
                tutor = UserOutput(
                    full_name=user.full_name,
                    email=user.email,
                    phone=user.phone,
                    status=user.status,
                    has_registered=user.has_registered,
                    is_verified=user.is_verified,
                    id=user.id,
                )
            service_payload["tutor"] = tutor
            service_payload["tutor_user_id"] = tutor.id if tutor else None
            service_data = ServiceOutput(**service_payload)

            tutor_entity = None
            if getattr(service, "service_tutor", None):
                tutor_entity = service.service_tutor
                tutor_payload = tutor_entity.to_dict()
                tutor_payload["user"] = tutor
                tutor_data = TutorOutput(**tutor_payload)

        if getattr(item, "service_booking_student", None):
            student = item.service_booking_student
            student_payload = student.to_dict()
            # to_dict() covers the student's own columns only, so the name lives
            # on the associated user. Without this the attendance list can show
            # a booking but not who made it.
            if getattr(student, "student_ura", None):
                student_user = student.student_ura[0].ura_user
                student_payload["user"] = (
                    UserOutput(
                        full_name=student_user.full_name,
                        email=student_user.email,
                        phone=student_user.phone,
                        status=student_user.status,
                        has_registered=student_user.has_registered,
                        is_verified=student_user.is_verified,
                        id=student_user.id,
                    )
                    if student_user
                    else None
                )
            student_data = StudentOutput(**student_payload)

        booking_payload["service"] = service_data
        booking_payload["student"] = student_data
        booking_payload["tutor"] = tutor_data
        booking_payload["reschedule_proposals"] = [
            RescheduleProposalOutput.model_validate(proposal, from_attributes=True)
            for proposal in getattr(item, "booking_reschedule_proposals", [])
        ]
        booking_outputs.append(ServiceBookingOutput(**booking_payload))

    return PaginatedServiceBookings(
        success=data["success"],
        message=data["message"],
        # The repository computes page counts, but they were being dropped here,
        # so clients had no way to page through bookings.
        metadata=data.get("metadata", {}),
        data=booking_outputs,
    )
