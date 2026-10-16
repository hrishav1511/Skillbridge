from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from skillbridge.api.repositories import chat as chat_repository
from skillbridge.api.repositories.chat import ChatRepository
from skillbridge.api.schemas.chat import SendMessagePayload
from skillbridge.database.models.sqlalchemy.chat_messages import ChatMessage
from skillbridge.database.models.sqlalchemy.chat_room_members import ChatRoomMember
from skillbridge.database.models.sqlalchemy.chat_rooms import ChatRoom
from skillbridge.database.models.sqlalchemy.message_read_status import MessageReadStatus
from skillbridge.database.models.sqlalchemy.users import User


@pytest.fixture
def chat_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(chat_repository, "get_session", session_context)
    return test_session


async def _seed_chat(session):
    sender = User(
        id=uuid4(), full_name="Sender", email="sender-chat@example.com", password="x"
    )
    reader = User(
        id=uuid4(), full_name="Reader", email="reader-chat@example.com", password="x"
    )
    room = ChatRoom(id=uuid4(), room_type="DIRECT")
    session.add_all(
        [
            sender,
            reader,
            room,
            ChatRoomMember(chat_room_id=room.id, user_id=sender.id),
            ChatRoomMember(chat_room_id=room.id, user_id=reader.id),
        ]
    )
    base = datetime(2026, 1, 1, 10, 0, 0)
    messages = [
        ChatMessage(
            id=UUID("ffffffff-ffff-4fff-8fff-ffffffffffff"),
            chat_room_id=room.id,
            sender_id=sender.id,
            content="oldest",
            created_at=base,
        ),
        ChatMessage(
            id=UUID("88888888-8888-4888-8888-888888888888"),
            chat_room_id=room.id,
            sender_id=sender.id,
            content="middle",
            created_at=base + timedelta(minutes=1),
        ),
        ChatMessage(
            id=UUID("00000000-0000-4000-8000-000000000001"),
            chat_room_id=room.id,
            sender_id=sender.id,
            content="newest",
            created_at=base + timedelta(minutes=2),
        ),
    ]
    session.add_all(messages)
    await session.flush()
    return sender, reader, room, messages


@pytest.mark.asyncio
async def test_room_preview_uses_message_time_not_random_uuid(chat_session):
    sender, _reader, room, _messages = await _seed_chat(chat_session)

    rooms = await ChatRepository().get_user_rooms(sender.id)

    assert len(rooms) == 1
    assert rooms[0]["chat_room_id"] == str(room.id)
    assert rooms[0]["last_message"]["content"] == "newest"


@pytest.mark.asyncio
async def test_history_cursor_uses_message_time(chat_session):
    _sender, _reader, room, messages = await _seed_chat(chat_session)

    history = await ChatRepository().get_history(
        room.id, before_message_id=messages[1].id
    )

    assert [message["content"] for message in history] == ["oldest"]


@pytest.mark.asyncio
async def test_mark_read_uses_message_time_and_correct_foreign_key(chat_session):
    _sender, reader, room, messages = await _seed_chat(chat_session)

    marked = await ChatRepository().mark_messages_read(
        room.id, reader.id, messages[1].id
    )

    assert set(marked) == {messages[0].id, messages[1].id}
    stored = (
        (
            await chat_session.execute(
                select(MessageReadStatus.chat_message_id).where(
                    MessageReadStatus.user_id == reader.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert set(stored) == set(marked)


@pytest.mark.parametrize("content", ["", "   ", "x" * 4001])
def test_message_content_is_bounded_and_non_blank(content):
    with pytest.raises(ValidationError):
        SendMessagePayload(chat_room_id=uuid4(), content=content)
