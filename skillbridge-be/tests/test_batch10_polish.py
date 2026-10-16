"""Polish & correctness batch.

  * a finished session must not hand out its joining link (item 23);
  * the chat room list must report per-room unread counts so the navbar can
    badge the number of conversations with unread messages (item 25).
"""

import uuid as _uuid
from datetime import datetime, timedelta, timezone

import pytest

from skillbridge.database.models.sqlalchemy.chat_messages import ChatMessage
from skillbridge.database.models.sqlalchemy.chat_room_members import ChatRoomMember
from skillbridge.database.models.sqlalchemy.chat_rooms import ChatRoom
from skillbridge.database.models.sqlalchemy.service_bookings import ServiceBooking

from tests.test_batch2_regressions import (  # noqa: F401  (fixtures)
    PASSWORD,
    _auth,
    client,
    student,
    world,
)


def _factory(test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# --------------------------------------------------------------------------
# Item 23 - a session that is over cannot be joined
# --------------------------------------------------------------------------


@pytest.fixture
def booking_at(test_engine, world, student):
    """An ACCEPTED booking whose session starts at a chosen time."""

    async def _make(start_at):
        factory = _factory(test_engine)
        async with factory() as session:
            booking = ServiceBooking(
                id=_uuid.uuid4(),
                service_id=_uuid.UUID(world["service"]),
                student_id=_uuid.UUID(student["student_id"]),
                status="ACCEPTED",
                scheduled_start_at=start_at,
            )
            session.add(booking)
            await session.commit()
            return str(booking.id)

    return _make


@pytest.mark.asyncio
async def test_a_finished_session_hides_its_joining_link(
    client, world, student, booking_at, test_engine
):
    """The service runs 13:30-14:30; a booking from last week is over."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from skillbridge.database.models.sqlalchemy.services import Service

    factory = _factory(test_engine)
    async with factory() as session:
        service = await session.get(Service, _uuid.UUID(world["service"]))
        # Without this the assertion would pass vacuously - the fixture service
        # has no joining link to withhold in the first place.
        service.joining_link = "https://meet.example.com/abc"
        await session.commit()

    await booking_at(datetime.now(timezone.utc) - timedelta(days=7))

    response = await client.get(
        "/api/v1/service-booking/service-bookings/",
        headers=_auth(student["user_id"]),
    )

    assert response.status_code == 200, response.text
    booking = response.json()["data"][0]
    assert booking["service"]["schedule_status"] == "COMPLETED"
    assert booking["service"]["joining_link"] is None


@pytest.mark.asyncio
async def test_a_running_session_still_offers_its_joining_link(
    client, world, student, booking_at, test_engine
):
    """Joining must stay possible while the session is actually running."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from skillbridge.database.models.sqlalchemy.services import Service

    factory = _factory(test_engine)
    async with factory() as session:
        service = await session.get(Service, _uuid.UUID(world["service"]))
        service.joining_link = "https://meet.example.com/abc"
        await session.commit()

    # Started 10 minutes ago, runs for an hour.
    await booking_at(datetime.now(timezone.utc) - timedelta(minutes=10))

    response = await client.get(
        "/api/v1/service-booking/service-bookings/",
        headers=_auth(student["user_id"]),
    )

    booking = response.json()["data"][0]
    assert booking["service"]["schedule_status"] == "RUNNING"
    assert booking["service"]["joining_link"] == "https://meet.example.com/abc"


# --------------------------------------------------------------------------
# Item 25 - unread counts per conversation
# --------------------------------------------------------------------------


@pytest.fixture
def room_with_messages(test_engine, world, student):
    """A direct room between the tutor and the student, with messages."""

    async def _make(message_count: int):
        factory = _factory(test_engine)
        async with factory() as session:
            room = ChatRoom(id=_uuid.uuid4(), room_type="DIRECT", status="ACTIVE")
            session.add(room)
            await session.flush()
            for user_id in (world["tutor_user"], student["user_id"]):
                session.add(
                    ChatRoomMember(
                        id=_uuid.uuid4(),
                        chat_room_id=room.id,
                        user_id=user_id,
                        status="ACTIVE",
                    )
                )
            base = datetime.now(timezone.utc) - timedelta(minutes=message_count)
            for index in range(message_count):
                session.add(
                    ChatMessage(
                        id=_uuid.uuid4(),
                        chat_room_id=room.id,
                        # Sent by the tutor, so they are unread for the student.
                        sender_id=world["tutor_user"],
                        content=f"message {index}",
                        created_at=base + timedelta(minutes=index),
                        is_deleted=False,
                        status="ACTIVE",
                    )
                )
            await session.commit()
            return str(room.id)

    return _make


@pytest.mark.asyncio
async def test_room_list_reports_unread_count(
    client, world, student, room_with_messages
):
    await room_with_messages(3)

    response = await client.get(
        "/api/v1/chat/rooms/", headers=_auth(student["user_id"])
    )

    assert response.status_code == 200, response.text
    room = response.json()[0]
    assert room["unread_count"] == 3


@pytest.mark.asyncio
async def test_own_messages_are_never_unread(
    client, world, student, room_with_messages
):
    """The tutor sent them, so the tutor has nothing unread."""
    await room_with_messages(3)

    response = await client.get(
        "/api/v1/chat/rooms/", headers=_auth(world["tutor_user"])
    )

    assert response.json()[0]["unread_count"] == 0


@pytest.mark.asyncio
async def test_reading_a_room_clears_its_unread_count(
    client, world, student, room_with_messages, test_engine
):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from skillbridge.api.repositories.chat import ChatRepository

    room_id = await room_with_messages(2)

    factory = _factory(test_engine)
    async with factory() as session:
        newest = (
            await session.execute(
                select(ChatMessage.id)
                .where(ChatMessage.chat_room_id == _uuid.UUID(room_id))
                .order_by(ChatMessage.created_at.desc())
            )
        ).scalars().first()

    await ChatRepository().mark_messages_read(
        chat_room_id=_uuid.UUID(room_id),
        user_id=student["user_id"],
        up_to_message_id=newest,
    )

    response = await client.get(
        "/api/v1/chat/rooms/", headers=_auth(student["user_id"])
    )

    assert response.json()[0]["unread_count"] == 0


# --------------------------------------------------------------------------
# Item 24 - upload caps
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oversized_service_image_is_rejected(client, world):
    """A file over the image cap must be refused, not stored."""
    from skillbridge.api.services.media_service import MediaService

    oversized = b"\xff\xd8\xff" + b"0" * (MediaService.SERVICE_IMAGE_MAX_MB * 1024 * 1024 + 1024)
    response = await client.post(
        "/api/v1/service/create/",
        data={
            "tutor_id": world["tutor"],
            "service_name": "Too big",
            "date": "2030-01-01",
            "time": "10:00",
            "end_time": "11:00",
            "price": "10",
            "level": "BEGINNER",
        },
        files={"images": ("big.jpg", oversized, "image/jpeg")},
        headers=_auth(world["tutor_user"]),
    )

    assert response.status_code == 400, response.status_code
    assert "too large" in response.text.lower()


@pytest.mark.asyncio
async def test_too_many_service_images_are_rejected(client, world):
    from skillbridge.api.services.media_service import MediaService

    one_pixel = b"\xff\xd8\xff" + b"0" * 128
    files = [
        ("images", (f"pic{index}.jpg", one_pixel, "image/jpeg"))
        for index in range(MediaService.MAX_SERVICE_IMAGES + 1)
    ]
    response = await client.post(
        "/api/v1/service/create/",
        data={
            "tutor_id": world["tutor"],
            "service_name": "Too many",
            "date": "2030-01-01",
            "time": "10:00",
            "end_time": "11:00",
            "price": "10",
            "level": "BEGINNER",
        },
        files=files,
        headers=_auth(world["tutor_user"]),
    )

    assert response.status_code == 422, response.text
    assert str(MediaService.MAX_SERVICE_IMAGES) in response.text


# --------------------------------------------------------------------------
# Service subject tags
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_tags_survive_create(client, world):
    """The create form sends tags as JSON; they must reach the revision.

    The API accepted tags all along, but the create/edit form had no field, so
    every service was stored with an empty list while the admin approval modal
    and the tutor search both read it.
    """
    import json

    response = await client.post(
        "/api/v1/service/create/",
        data={
            "tutor_id": world["tutor"],
            "service_name": "Tagged service",
            "date": "2030-01-01",
            "time": "10:00",
            "end_time": "11:00",
            "price": "10",
            "level": "BEGINNER",
            "tags": json.dumps(["Python", "Data Structures"]),
        },
        headers=_auth(world["tutor_user"]),
    )

    assert response.status_code in (200, 201), response.text
    assert response.json()["data"]["tags"] == ["Python", "Data Structures"]


@pytest.mark.asyncio
async def test_service_tags_accept_a_comma_separated_list(client, world):
    """The API also parses CSV, so a hand-typed value still works."""
    response = await client.post(
        "/api/v1/service/create/",
        data={
            "tutor_id": world["tutor"],
            "service_name": "CSV tagged",
            "date": "2030-01-01",
            "time": "10:00",
            "end_time": "11:00",
            "price": "10",
            "level": "BEGINNER",
            "tags": "Algebra, Calculus",
        },
        headers=_auth(world["tutor_user"]),
    )

    assert response.status_code in (200, 201), response.text
    assert response.json()["data"]["tags"] == ["Algebra", "Calculus"]


@pytest.mark.asyncio
async def test_a_service_tag_is_searchable(client, world, test_engine):
    """A tagged service must be findable by that tag in tutor search."""
    import uuid as _u
    from datetime import date as _date, time as _time
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from skillbridge.database.models.sqlalchemy.services import Service

    factory = _factory(test_engine)
    async with factory() as session:
        session.add(
            Service(
                id=_u.uuid4(),
                tutor_id=_u.UUID(world["tutor"]),
                service_name="Quantum tutoring",
                description="d",
                date=_date(2030, 1, 1),
                time=_time(10, 0),
                end_time=_time(11, 0),
                price=10,
                level="BEGINNER",
                tags=["Zylotronics"],
                status="ACTIVE",
            )
        )
        await session.commit()

    response = await client.get(
        "/api/v1/tutor/tutors/", params={"query": "Zylotronics"}
    )

    assert response.status_code == 200
    assert response.json()["data"], "a service tag must match in tutor search"
