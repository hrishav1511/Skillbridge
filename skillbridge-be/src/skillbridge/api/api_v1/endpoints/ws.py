import json
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError
from sqlalchemy import func, select

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.api.repositories.chat import ChatRepository
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.schemas.chat import (
    CheckDirectRoomResponse,
    SendMessagePayload,
    FetchHistoryPayload,
    MarkReadPayload,
    TypingPayload,
    CreateDirectRoomRequest,
    CreateGroupRoomRequest,
)
from skillbridge.utils.websocket.managers import manager
from skillbridge.utils.websocket import payloads as P
from skillbridge.database.db.database import get_session
from skillbridge.utils.service_time import utc_isoformat
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User

router = APIRouter(tags=["chat"])


def get_token_user_id(current_user: dict) -> UUID:
    return UUID(current_user["sub"])


async def _get_active_user_roles(user_id: UUID) -> set[str]:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if user is None or str(user.status).upper() != "ACTIVE":
            raise HTTPException(
                status_code=403, detail="The target account is unavailable."
            )
        result = await session.execute(
            select(func.lower(Role.slug), UserRoleAssociation.tutor_id)
            .join(UserRoleAssociation, UserRoleAssociation.role_id == Role.id)
            .where(UserRoleAssociation.user_id == user_id)
        )
        roles = set()
        tutor_ids = set()
        for slug, tutor_id in result.all():
            roles.add(slug)
            if tutor_id is not None:
                tutor_ids.add(tutor_id)

        # A deactivated tutor keeps their login but leaves the marketplace, and
        # "cannot be messaged" is part of leaving it. The tutor role is dropped
        # rather than the account refused, so the tutor can still be reached in
        # whatever other role they hold.
        if tutor_ids:
            active_tutor = (
                await session.execute(
                    select(func.count(Tutor.id)).where(
                        Tutor.id.in_(tutor_ids),
                        func.upper(Tutor.status) == "ACTIVE",
                    )
                )
            ).scalar_one()
            if not active_tutor:
                roles.discard("tutor")
        return roles


async def _ensure_direct_chat_allowed(user_id: UUID, target_user_id: UUID) -> None:
    source_roles = await _get_active_user_roles(user_id)
    target_roles = await _get_active_user_roles(target_user_id)
    allowed_pairs = {
        frozenset(("student", "tutor")),
        frozenset(("admin", "tutor")),
        frozenset(("super_admin", "tutor")),
    }
    if not any(
        frozenset((source_role, target_role)) in allowed_pairs
        for source_role in source_roles
        for target_role in target_roles
    ):
        raise HTTPException(
            status_code=403, detail="This conversation is not permitted."
        )


# ── REST endpoints ────────────────────────────────────────────────────────────


@router.post("/rooms/direct/")
@validate_token
async def create_direct_room(
    request: Request,
    target_user_id: UUID,
    user_id: UUID | None = None,
):

    if user_id == target_user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot create a direct chat room with yourself.",
        )

    await _ensure_direct_chat_allowed(user_id, target_user_id)

    room = await ChatRepository().get_or_create_direct_room(
        user_id,
        target_user_id,
    )
    return {"chat_room_id": room.id, "room_type": room.room_type}


@router.get(
    "/rooms/direct/",
    response_model=CheckDirectRoomResponse,
)
@validate_token
async def check_direct_room(
    request: Request,
    target_user_id: UUID,
    user_id: UUID | None = None,
):
    """Check whether a direct chat room already exists between two users."""
    room = await ChatRepository().get_direct_room(user_id, target_user_id)
    return {
        "room_exists": bool(room),
        "chat_room_id": str(room.id) if room else None,
    }


@router.post("/rooms/group/")
@validate_token
async def create_group_room(
    request: Request,
    create_group_room_input: CreateGroupRoomRequest,
    user_id: UUID | None = None,
):
    creator_roles = await _get_active_user_roles(user_id)
    if not creator_roles.intersection({"admin", "super_admin"}):
        raise HTTPException(
            status_code=403, detail="Admin access required for group chats."
        )
    member_ids = list(create_group_room_input.member_ids)
    if user_id not in member_ids:
        member_ids.append(user_id)
    for member_id in member_ids:
        await _get_active_user_roles(member_id)
    room = await ChatRepository().create_group_room(
        create_group_room_input.name,
        member_ids,
    )
    return {"chat_room_id": room.id, "name": room.name}


@router.get("/rooms/")
@validate_token
async def list_my_rooms(
    request: Request,
    user_id: UUID | None = None,
):
    """
    Chat inbox / chat-head list.

    Returns every room the user belongs to, each with the other member's
    name + email and a preview of the last message, so the frontend can
    render the inbox screen with a single call.
    """
    rooms = await ChatRepository().get_user_rooms(user_id=user_id)
    return rooms


@router.get("/rooms/{chat_room_id}/")
@validate_token
async def get_room(
    request: Request,
    chat_room_id: UUID,
    user_id: UUID | None = None,
):
    """
    Details for a single room: name, type, and full member list
    (with full_name/email). Used to render a chat header, e.g.
    "Chatting with Bob Smith".
    """
    repo = ChatRepository()

    if not await repo.is_member(chat_room_id, user_id):
        raise HTTPException(
            status_code=403, detail="You are not a member of this room."
        )

    room = await repo.get_room_details(chat_room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    return room


@router.get("/rooms/{chat_room_id}/messages/")
@validate_token
async def get_room_messages(
    request: Request,
    chat_room_id: UUID,
    before_message_id: UUID | None = Query(default=None),
    limit: int = Query(default=30, le=100),
    user_id: UUID | None = None,
):
    """
    Fetch message history for a room. This is what the frontend calls the
    moment a user clicks a chat head and opens a conversation — a plain
    REST call, so it doesn't need to wait on the WebSocket connection
    being ready first.

    Each message includes the sender's full_name/email, so the frontend
    can render "Bob: hello" directly with no extra lookups.

    For pagination while scrolling up inside an already-open room, the
    WebSocket "fetch_history" message type does the same job and is
    preferred there since the connection is already live.
    """
    repo = ChatRepository()

    if not await repo.is_member(chat_room_id, user_id):
        raise HTTPException(
            status_code=403, detail="You are not a member of this room."
        )

    messages = await repo.get_history(
        chat_room_id=chat_room_id,
        before_message_id=before_message_id,
        limit=limit,
    )
    return {"chat_room_id": str(chat_room_id), "messages": messages}


# ── WebSocket ─────────────────────────────────────────────────────────────────


@router.websocket("/ws/{user_id}")
async def chat_websocket(
    websocket: WebSocket,
    user_id: UUID,
):
    """
    Single WebSocket per user. Handles all rooms they belong to.

    Incoming frame structure (JSON text):
    {
        "type":    "send_message" | "fetch_history" | "mark_read" | "typing",
        "payload": { ... }          # see schemas/chat.py
    }

    Outgoing frame structure (JSON text):
    {
        "event":   "new_message" | "history" | "read_receipt" | "typing" | "error",
        "payload": { ... }
    }
    """

    token = websocket.query_params.get("token")
    try:
        token_repo = TokenRepository()
        payload = await token_repo.verify_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="An access token is required.")
        authenticated_user_id = UUID(str(payload.get("sub", "")))
        if authenticated_user_id != user_id:
            raise HTTPException(status_code=403, detail="WebSocket identity mismatch.")
        async with get_session() as session:
            user = await session.get(User, authenticated_user_id)
            if user is None or str(user.status).upper() != "ACTIVE":
                raise HTTPException(
                    status_code=403, detail="Account is inactive or unavailable."
                )
    except (HTTPException, TypeError, ValueError):
        await websocket.close(code=4401, reason="WebSocket authentication failed.")
        return

    await manager.connect(websocket, str(authenticated_user_id))
    user_id = authenticated_user_id
    repo = ChatRepository()

    async def send_pending_notifications() -> None:
        notification_repository = NotificationRepository()
        notifications = await notification_repository.list_undelivered_for_user(
            user_id=user_id,
            limit=100,
        )
        for notification in notifications:
            await websocket.send_json(
                {
                    "event": P.EVENT_NOTIFICATION,
                    "payload": notification.model_dump(mode="json"),
                }
            )
            await notification_repository.mark_delivered(
                notification_id=notification.id,
                user_id=user_id,
            )

    try:
        await send_pending_notifications()
    except Exception:
        # A notification sync failure must not prevent chat from connecting.
        pass

    async def send_error(message: str) -> None:
        await websocket.send_json(
            {"event": P.EVENT_ERROR, "payload": {"message": message}}
        )

    async def ensure_member(chat_room_id: UUID) -> bool:
        if await repo.is_member(chat_room_id, user_id):
            return True
        await send_error("You are not a member of this room.")
        return False

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                frame = json.loads(raw)
                if not isinstance(frame, dict):
                    raise ValueError("Frame must be a JSON object.")

                msg_type = frame.get("type")
                payload = frame.get("payload", {})
                if not isinstance(payload, dict):
                    raise ValueError("Payload must be a JSON object.")

                if msg_type == P.TYPE_SEND_MESSAGE:
                    data = SendMessagePayload.model_validate(payload)
                    if not await ensure_member(data.chat_room_id):
                        continue

                    msg, message_notifications, was_created = (
                        await repo.save_message_with_notifications(
                            chat_room_id=data.chat_room_id,
                            sender_id=user_id,
                            content=data.content,
                            client_message_id=data.client_message_id,
                        )
                    )
                    if not was_created:
                        continue
                    outgoing = {
                        "event": P.EVENT_NEW_MESSAGE,
                        "payload": {
                            "id": str(msg.id),
                            "chat_room_id": str(msg.chat_room_id),
                            "sender_id": str(msg.sender_id),
                            "content": msg.content,
                            "created_at": utc_isoformat(msg.created_at),
                        },
                    }
                    for member_id in await repo.get_room_member_ids(data.chat_room_id):
                        await manager.send_to_user(str(member_id), outgoing)
                    for notification in message_notifications:
                        await NotificationRepository().deliver_live(notification)

                elif msg_type == P.TYPE_FETCH_HISTORY:
                    data = FetchHistoryPayload.model_validate(payload)
                    if not await ensure_member(data.chat_room_id):
                        continue

                    messages = await repo.get_history(
                        chat_room_id=data.chat_room_id,
                        before_message_id=data.before_message_id,
                        limit=data.limit,
                    )
                    await websocket.send_json(
                        {
                            "event": P.EVENT_HISTORY,
                            "payload": {
                                "chat_room_id": str(data.chat_room_id),
                                "messages": messages,
                            },
                        }
                    )

                elif msg_type == P.TYPE_MARK_READ:
                    data = MarkReadPayload.model_validate(payload)
                    if not await ensure_member(data.chat_room_id):
                        continue

                    newly_read_ids = await repo.mark_messages_read(
                        chat_room_id=data.chat_room_id,
                        user_id=user_id,
                        up_to_message_id=data.message_id,
                    )
                    if newly_read_ids:
                        receipt = {
                            "event": P.EVENT_READ_RECEIPT,
                            "payload": {
                                "chat_room_id": str(data.chat_room_id),
                                "read_by": str(user_id),
                                "message_ids": [
                                    str(message_id) for message_id in newly_read_ids
                                ],
                            },
                        }
                        for member_id in await repo.get_room_member_ids(
                            data.chat_room_id
                        ):
                            if member_id != user_id:
                                await manager.send_to_user(str(member_id), receipt)

                elif msg_type == P.TYPE_TYPING:
                    data = TypingPayload.model_validate(payload)
                    if not await ensure_member(data.chat_room_id):
                        continue

                    typing_event = {
                        "event": P.EVENT_TYPING,
                        "payload": {
                            "chat_room_id": str(data.chat_room_id),
                            "user_id": str(user_id),
                            "is_typing": data.is_typing,
                        },
                    }
                    for member_id in await repo.get_room_member_ids(data.chat_room_id):
                        if member_id != user_id:
                            await manager.send_to_user(str(member_id), typing_event)

                else:
                    await send_error(f"Unknown message type: {msg_type}")

            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
                ValidationError,
            ) as exc:
                await send_error(f"Invalid WebSocket message: {exc}")
            except WebSocketDisconnect:
                raise
            except Exception:
                await send_error("Unable to process WebSocket message.")

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(str(user_id), websocket)
