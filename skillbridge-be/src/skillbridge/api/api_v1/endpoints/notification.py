from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.schemas.notification import (
    NotificationListResponse,
    NotificationOutput,
    NotificationResponse,
)
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


@router.get(
    "/",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def list_notifications(
    request: Request,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID | None = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return NotificationListResponse(
        **await NotificationRepository().list_for_user(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
    )


@router.patch(
    "/{notification_id}/read/",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def mark_notification_read(
    request: Request,
    notification_id: UUID,
    user_id: UUID | None = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    notification = await NotificationRepository().mark_read(
        notification_id=notification_id,
        user_id=user_id,
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return NotificationResponse(
        success=True,
        message="Notification marked as read.",
        data=NotificationOutput.model_validate(notification),
    )


@router.patch(
    "/read-all/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def mark_all_notifications_read(
    request: Request,
    user_id: UUID | None = None,
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    count = await NotificationRepository().mark_all_read(user_id=user_id)
    return {
        "success": True,
        "message": "Notifications marked as read.",
        "data": {"updated_count": count},
    }