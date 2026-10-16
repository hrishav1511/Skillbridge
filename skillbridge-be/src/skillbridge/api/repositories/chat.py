from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, case, or_, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.database.db.database import get_session
from skillbridge.utils.service_time import utc_isoformat
from skillbridge.database.models.sqlalchemy.chat_messages import ChatMessage
from skillbridge.database.models.sqlalchemy.chat_room_members import ChatRoomMember
from skillbridge.database.models.sqlalchemy.chat_rooms import ChatRoom
from skillbridge.database.models.sqlalchemy.message_read_status import MessageReadStatus
from skillbridge.database.models.sqlalchemy.users import (
    User,
)  # adjust path/class name if different


class ChatRepository:
    # ── Rooms ─────────────────────────────────────────────────────────────────

    async def get_or_create_direct_room(
        self,
        user_a: UUID,
        user_b: UUID,
    ) -> ChatRoom:
        """
        Find an existing direct room shared by exactly these two users,
        or create a new one.
        """
        if user_a == user_b:
            raise ValueError("Cannot create a direct chat room with the same user.")

        matching_room_ids = self._direct_room_ids_for_users(user_a, user_b).subquery()
        stmt = (
            select(ChatRoom)
            .where(ChatRoom.id.in_(select(matching_room_ids.c.chat_room_id)))
            .limit(1)
        )

        async with get_session() as session:
            result = await session.execute(stmt)
            room = result.scalar_one_or_none()

            if room:
                return room

            room = ChatRoom(room_type="DIRECT")
            session.add(room)
            await session.flush()

            session.add_all(
                [
                    ChatRoomMember(chat_room_id=room.id, user_id=user_a),
                    ChatRoomMember(chat_room_id=room.id, user_id=user_b),
                ]
            )
            await session.commit()
            await session.refresh(room)
            return room

    async def get_direct_room(
        self,
        user_a: UUID,
        user_b: UUID,
    ) -> ChatRoom | None:
        """Return an existing direct room between two users, or None."""
        if user_a == user_b:
            return None

        matching_room_ids = self._direct_room_ids_for_users(user_a, user_b).subquery()
        stmt = (
            select(ChatRoom)
            .where(ChatRoom.id.in_(select(matching_room_ids.c.chat_room_id)))
            .limit(1)
        )

        async with get_session() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    def _direct_room_ids_for_users(self, user_a: UUID, user_b: UUID):
        target_member = case(
            (ChatRoomMember.user_id.in_([user_a, user_b]), ChatRoomMember.user_id),
            else_=None,
        )

        return (
            select(ChatRoomMember.chat_room_id)
            .join(ChatRoom, ChatRoom.id == ChatRoomMember.chat_room_id)
            .where(ChatRoom.room_type == "DIRECT")
            .group_by(ChatRoomMember.chat_room_id)
            .having(func.count(func.distinct(ChatRoomMember.user_id)) == 2)
            .having(func.count(func.distinct(target_member)) == 2)
        )

    async def create_group_room(
        self,
        name: str,
        member_ids: list[UUID],
    ) -> ChatRoom:
        room = ChatRoom(name=name, room_type="GROUP")

        async with get_session() as session:
            session.add(room)
            await session.flush()

            session.add_all(
                [
                    ChatRoomMember(chat_room_id=room.id, user_id=uid)
                    for uid in member_ids
                ]
            )
            await session.commit()
            await session.refresh(room)
            return room

    async def get_user_rooms(
        self,
        user_id: UUID,
    ) -> list[dict]:
        """
        Returns every room the user belongs to, each enriched with:
          - the other member(s)' full_name/email (for direct rooms, this is
            "who am I chatting with"; for group rooms, all other members)
          - a preview of the most recent message, if any

        This is what powers the chat-head / inbox list: the frontend can
        render name + last message + room id directly from this response,
        with no further lookups needed.
        """
        # 1. Get the room ids + room_type/name this user belongs to
        stmt = (
            select(ChatRoom)
            .join(ChatRoomMember, ChatRoom.id == ChatRoomMember.chat_room_id)
            .where(ChatRoomMember.user_id == user_id)
            .distinct()
        )

        async with get_session() as session:
            result = await session.execute(stmt)
            rooms = result.scalars().all()

            if not rooms:
                return []

            room_ids = [r.id for r in rooms]

            # 2. Get every OTHER member (with user info) for these rooms in one query
            other_members_stmt = (
                select(
                    ChatRoomMember.chat_room_id,
                    User.id.label("user_id"),
                    User.full_name,
                    User.email,
                )
                .distinct()
                .join(User, User.id == ChatRoomMember.user_id)
                .where(
                    ChatRoomMember.chat_room_id.in_(room_ids),
                    ChatRoomMember.user_id != user_id,
                )
            )
            other_members_result = await session.execute(other_members_stmt)

            members_by_room: dict[UUID, list[dict]] = {}
            for row in other_members_result.all():
                members_by_room.setdefault(row.chat_room_id, []).append(
                    {
                        "user_id": str(row.user_id),
                        "full_name": row.full_name,
                        "email": row.email,
                    }
                )

            # 3. Select the newest message chronologically. Message ids are
            # UUID4 values, so MAX(id) does not mean "latest".
            ranked_messages = (
                select(
                    ChatMessage.id.label("message_id"),
                    func.row_number()
                    .over(
                        partition_by=ChatMessage.chat_room_id,
                        order_by=(ChatMessage.created_at.desc(), ChatMessage.id.desc()),
                    )
                    .label("position"),
                )
                .where(
                    ChatMessage.chat_room_id.in_(room_ids),
                    ChatMessage.is_deleted == False,
                )
                .subquery()
            )
            latest_msg_stmt = (
                select(ChatMessage)
                .join(ranked_messages, ChatMessage.id == ranked_messages.c.message_id)
                .where(ranked_messages.c.position == 1)
            )
            latest_msg_result = await session.execute(latest_msg_stmt)

            last_message_by_room: dict[UUID, dict] = {
                msg.chat_room_id: {
                    "id": str(msg.id),
                    "sender_id": str(msg.sender_id),
                    "content": msg.content,
                    "created_at": utc_isoformat(msg.created_at),
                }
                for msg in latest_msg_result.scalars().all()
            }

            # 3b. Unread per room: messages someone else sent that this
            # user has no read receipt for. The navbar badges the number of
            # conversations with unread messages, so the count has to be per
            # room rather than a single total.
            already_read = select(MessageReadStatus.chat_message_id).where(
                MessageReadStatus.user_id == user_id
            )
            unread_stmt = (
                select(ChatMessage.chat_room_id, func.count(ChatMessage.id))
                .where(
                    ChatMessage.chat_room_id.in_(room_ids),
                    ChatMessage.is_deleted == False,
                    ChatMessage.sender_id != user_id,
                    ChatMessage.id.not_in(already_read),
                )
                .group_by(ChatMessage.chat_room_id)
            )
            unread_by_room = {
                room_id: int(count)
                for room_id, count in (await session.execute(unread_stmt)).all()
            }

            # 4. Assemble final response per room
            output = []
            for room in rooms:
                other_members = members_by_room.get(room.id, [])
                if room.room_type == "DIRECT" and not other_members:
                    continue

                output.append(
                    {
                        "chat_room_id": str(room.id),
                        "name": room.name,
                        "room_type": room.room_type,
                        # For a DIRECT room this is exactly one user — the person
                        # you're chatting with. For GROUP rooms it's everyone else.
                        "members": other_members,
                        "last_message": last_message_by_room.get(room.id),
                        "unread_count": unread_by_room.get(room.id, 0),
                    }
                )

            # Most recently active rooms first
            output.sort(
                key=lambda r: (
                    r["last_message"]["created_at"] if r["last_message"] else ""
                ),
                reverse=True,
            )
            return output

    async def get_room_details(
        self,
        chat_room_id: UUID,
    ) -> dict | None:
        """
        Full member list (with names/emails) for a single room.
        Used for a chat header, e.g. "Chatting with Bob Smith" or a
        group member list.
        """
        room_stmt = select(ChatRoom).where(ChatRoom.id == chat_room_id)

        members_stmt = (
            select(
                User.id.label("user_id"),
                User.full_name,
                User.email,
            )
            .distinct()
            .join(ChatRoomMember, ChatRoomMember.user_id == User.id)
            .where(ChatRoomMember.chat_room_id == chat_room_id)
        )

        async with get_session() as session:
            room_result = await session.execute(room_stmt)
            room = room_result.scalar_one_or_none()
            if room is None:
                return None

            members_result = await session.execute(members_stmt)
            members = [
                {
                    "user_id": str(row.user_id),
                    "full_name": row.full_name,
                    "email": row.email,
                }
                for row in members_result.all()
            ]

            return {
                "chat_room_id": str(room.id),
                "name": room.name,
                "room_type": room.room_type,
                "members": members,
            }

    async def get_room_member_ids(
        self,
        chat_room_id: UUID,
    ) -> list[UUID]:
        stmt = (
            select(ChatRoomMember.user_id)
            .where(ChatRoomMember.chat_room_id == chat_room_id)
            .distinct()
        )

        async with get_session() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def is_member(
        self,
        chat_room_id: UUID,
        user_id: UUID,
    ) -> bool:
        stmt = (
            select(ChatRoomMember.user_id)
            .where(
                ChatRoomMember.chat_room_id == chat_room_id,
                ChatRoomMember.user_id == user_id,
            )
            .limit(1)
        )

        async with get_session() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    # ── Messages ──────────────────────────────────────────────────────────────

    async def save_message(
        self,
        chat_room_id: UUID,
        sender_id: UUID,
        content: str,
    ) -> ChatMessage:
        msg = ChatMessage(
            chat_room_id=chat_room_id, sender_id=sender_id, content=content
        )

        async with get_session() as session:
            session.add(msg)
            await session.commit()
            await session.refresh(msg)
            return msg

    async def save_message_with_notifications(
        self,
        chat_room_id: UUID,
        sender_id: UUID,
        content: str,
        client_message_id: UUID | None = None,
    ) -> tuple[ChatMessage, list, bool]:
        """Persist a message and recipient notifications in one transaction."""
        async with get_session() as session:
            if client_message_id is not None:
                existing_message = (
                    await session.execute(
                        select(ChatMessage).where(
                            ChatMessage.sender_id == sender_id,
                            ChatMessage.client_message_id == client_message_id,
                        )
                    )
                ).scalar_one_or_none()
                if existing_message is not None:
                    return existing_message, [], False
            sender_name = (
                await session.execute(
                    select(User.full_name).where(User.id == sender_id)
                )
            ).scalar_one_or_none() or "a SkillBridge user"
            recipient_ids = list(
                (
                    await session.execute(
                        select(ChatRoomMember.user_id)
                        .where(
                            ChatRoomMember.chat_room_id == chat_room_id,
                            ChatRoomMember.user_id != sender_id,
                        )
                        .distinct()
                    )
                )
                .scalars()
                .all()
            )
            msg = ChatMessage(
                chat_room_id=chat_room_id,
                sender_id=sender_id,
                content=content,
                client_message_id=client_message_id,
            )
            session.add(msg)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                if client_message_id is None:
                    raise
                existing_message = (
                    await session.execute(
                        select(ChatMessage).where(
                            ChatMessage.sender_id == sender_id,
                            ChatMessage.client_message_id == client_message_id,
                        )
                    )
                ).scalar_one_or_none()
                if existing_message is None:
                    raise
                return existing_message, [], False
            await session.refresh(msg)
            notifications = []
            for recipient_id in recipient_ids:
                notifications.append(
                    await NotificationRepository().create_for_user(
                        user_id=recipient_id,
                        notification_type="CHAT_MESSAGE_RECEIVED",
                        title=f"New message from {sender_name}",
                        message=content[:240],
                        data={
                            "message_id": str(msg.id),
                            "chat_room_id": str(chat_room_id),
                            "sender_id": str(sender_id),
                        },
                        session=session,
                    )
                )
            await session.commit()
            return msg, notifications, True

    async def get_history(
        self,
        chat_room_id: UUID,
        before_message_id: UUID | None = None,
        limit: int = 30,
    ) -> list[dict]:
        """
        Returns message history for a room, each message enriched with the
        sender's full_name/email so the frontend can render "Bob: hello"
        without a separate user lookup per message.
        """
        stmt = (
            select(
                ChatMessage.id,
                ChatMessage.chat_room_id,
                ChatMessage.sender_id,
                ChatMessage.content,
                ChatMessage.created_at,
                User.full_name.label("sender_full_name"),
                User.email.label("sender_email"),
            )
            .join(User, User.id == ChatMessage.sender_id)
            .where(
                ChatMessage.chat_room_id == chat_room_id,
                ChatMessage.is_deleted == False,
            )
        )
        async with get_session() as session:
            if before_message_id:
                cursor_created_at = (
                    await session.execute(
                        select(ChatMessage.created_at).where(
                            ChatMessage.id == before_message_id,
                            ChatMessage.chat_room_id == chat_room_id,
                        )
                    )
                ).scalar_one_or_none()
                if cursor_created_at is None:
                    return []
                stmt = stmt.where(
                    or_(
                        ChatMessage.created_at < cursor_created_at,
                        and_(
                            ChatMessage.created_at == cursor_created_at,
                            ChatMessage.id < before_message_id,
                        ),
                    )
                )

            stmt = stmt.order_by(
                ChatMessage.created_at.desc(), ChatMessage.id.desc()
            ).limit(limit)
            result = await session.execute(stmt)
            rows = result.all()

            return [
                {
                    "id": str(row.id),
                    "chat_room_id": str(row.chat_room_id),
                    "sender_id": str(row.sender_id),
                    "sender_full_name": row.sender_full_name,
                    "sender_email": row.sender_email,
                    "content": row.content,
                    "created_at": utc_isoformat(row.created_at),
                }
                for row in rows
            ]

    # ── Read receipts ─────────────────────────────────────────────────────────

    async def mark_messages_read(
        self,
        chat_room_id: UUID,
        user_id: UUID,
        up_to_message_id: UUID,
    ) -> list[UUID]:
        """
        Insert read receipts for all unread messages in the room
        up to and including `up_to_message_id`.
        """
        async with get_session() as session:
            cursor_created_at = (
                await session.execute(
                    select(ChatMessage.created_at).where(
                        ChatMessage.id == up_to_message_id,
                        ChatMessage.chat_room_id == chat_room_id,
                    )
                )
            ).scalar_one_or_none()
            if cursor_created_at is None:
                return []

            already_read = select(MessageReadStatus.chat_message_id).where(
                MessageReadStatus.user_id == user_id
            )
            stmt = select(ChatMessage.id).where(
                ChatMessage.chat_room_id == chat_room_id,
                or_(
                    ChatMessage.created_at < cursor_created_at,
                    and_(
                        ChatMessage.created_at == cursor_created_at,
                        ChatMessage.id <= up_to_message_id,
                    ),
                ),
                ChatMessage.sender_id != user_id,
                ChatMessage.id.not_in(already_read),
            )
            result = await session.execute(stmt)
            unread_ids = result.scalars().all()

            if unread_ids:
                now = datetime.now(timezone.utc)
                session.add_all(
                    [
                        MessageReadStatus(
                            chat_message_id=mid, user_id=user_id, read_at=now
                        )
                        for mid in unread_ids
                    ]
                )
                await session.commit()

            return unread_ids
