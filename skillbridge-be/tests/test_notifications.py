from contextlib import asynccontextmanager
from uuid import uuid4
from datetime import date, time

import pytest
from sqlalchemy import select

from skillbridge.api.repositories import notification as notification_repository
from skillbridge.api.repositories import chat as chat_repository
from skillbridge.api.repositories.chat import ChatRepository
from skillbridge.api.repositories.review import ReviewRepository
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.database.models.sqlalchemy.chat_rooms import ChatRoom
from skillbridge.database.models.sqlalchemy.chat_room_members import ChatRoomMember
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)


@pytest.fixture
def notifications_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(notification_repository, "get_session", session_context)
    return test_session


@pytest.mark.asyncio
async def test_notifications_are_scoped_to_recipient_and_track_unread_state(
    notifications_session,
):
    recipient_id = uuid4()
    other_user_id = uuid4()
    notifications_session.add_all(
        [
            User(
                id=recipient_id,
                full_name="Tutor",
                email="tutor@example.com",
                password="x",
            ),
            User(
                id=other_user_id,
                full_name="Other",
                email="other@example.com",
                password="x",
            ),
            Notification(
                user_id=recipient_id,
                notification_type="SERVICE_APPROVED",
                title="Service approved",
                message="Your service was approved.",
                data={"service_id": str(uuid4())},
            ),
            Notification(
                user_id=other_user_id,
                notification_type="SERVICE_APPROVED",
                title="Service approved",
                message="This belongs to another user.",
                data={},
            ),
        ]
    )
    await notifications_session.flush()

    result = await NotificationRepository().list_for_user(user_id=recipient_id)

    assert len(result["data"]) == 1
    assert result["metadata"]["unread_count"] == 1
    assert result["data"][0].user_id == recipient_id


@pytest.mark.asyncio
async def test_mark_read_and_mark_all_read_are_idempotent(notifications_session):
    recipient_id = uuid4()
    notifications_session.add(
        User(
            id=recipient_id, full_name="Tutor", email="tutor@example.com", password="x"
        )
    )
    notifications = [
        Notification(
            user_id=recipient_id,
            notification_type="SERVICE_REVISION_APPROVED",
            title="Revision approved",
            message="Your revision was approved.",
            data={},
        ),
        Notification(
            user_id=recipient_id,
            notification_type="SERVICE_APPROVED",
            title="Service approved",
            message="Your service was approved.",
            data={},
        ),
    ]
    notifications_session.add_all(notifications)
    await notifications_session.flush()

    marked = await NotificationRepository().mark_read(
        notification_id=notifications[0].id,
        user_id=recipient_id,
    )
    updated_count = await NotificationRepository().mark_all_read(user_id=recipient_id)
    second_updated_count = await NotificationRepository().mark_all_read(
        user_id=recipient_id
    )

    assert marked.is_read is True
    assert updated_count == 1
    assert second_updated_count == 0


@pytest.mark.asyncio
async def test_booking_and_upcoming_service_update_notification_contract(
    notifications_session,
):
    recipient_id = uuid4()
    notifications_session.add(
        User(
            id=recipient_id,
            full_name="Tutor",
            email="contract@example.com",
            password="x",
        )
    )
    notifications_session.add_all(
        [
            Notification(
                user_id=recipient_id,
                notification_type="SERVICE_BOOKED",
                title="New service booking",
                message="A student booked your service.",
                data={
                    "booking_id": str(uuid4()),
                    "service_id": str(uuid4()),
                    "student_id": str(uuid4()),
                },
            ),
            Notification(
                user_id=recipient_id,
                notification_type="SERVICE_UPDATED",
                title="Booked service updated",
                message="A booked service was updated.",
                data={
                    "revision_id": str(uuid4()),
                    "service_id": str(uuid4()),
                    "revision_type": "UPDATE",
                },
            ),
        ]
    )
    await notifications_session.flush()

    result = await NotificationRepository().list_for_user(user_id=recipient_id)

    assert {item.notification_type for item in result["data"]} == {
        "SERVICE_BOOKED",
        "SERVICE_UPDATED",
    }


@pytest.mark.asyncio
async def test_undelivered_notifications_are_selected_and_marked_delivered(
    notifications_session,
):
    recipient_id = uuid4()
    notifications_session.add(
        User(
            id=recipient_id,
            full_name="Tutor",
            email="delivery@example.com",
            password="x",
        )
    )
    pending = Notification(
        user_id=recipient_id,
        notification_type="SERVICE_APPROVED",
        title="Service approved",
        message="Your service was approved.",
        data={},
    )
    already_delivered = Notification(
        user_id=recipient_id,
        notification_type="SERVICE_BOOKED",
        title="New service booking",
        message="A student booked your service.",
        data={},
        is_delivered=True,
    )
    notifications_session.add_all([pending, already_delivered])
    await notifications_session.flush()

    undelivered = await NotificationRepository().list_undelivered_for_user(
        user_id=recipient_id
    )
    assert [item.id for item in undelivered] == [pending.id]

    assert (
        await NotificationRepository().mark_delivered(
            notification_id=pending.id,
            user_id=recipient_id,
        )
        is True
    )
    assert pending.is_delivered is True


@pytest.mark.asyncio
async def test_chat_message_notifies_other_members_but_not_sender(
    test_session, monkeypatch
):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(chat_repository, "get_session", session_context)
    sender = User(
        id=uuid4(), full_name="Sender Name", email="sender@example.com", password="x"
    )
    recipient = User(
        id=uuid4(), full_name="Recipient", email="recipient@example.com", password="x"
    )
    room = ChatRoom(id=uuid4(), room_type="DIRECT")
    test_session.add_all(
        [
            sender,
            recipient,
            room,
            ChatRoomMember(chat_room_id=room.id, user_id=sender.id),
            ChatRoomMember(chat_room_id=room.id, user_id=recipient.id),
        ]
    )
    await test_session.flush()

    client_message_id = uuid4()
    (
        message,
        notifications,
        was_created,
    ) = await ChatRepository().save_message_with_notifications(
        room.id, sender.id, "Hello from the chat", client_message_id
    )

    assert was_created is True
    assert len(notifications) == 1
    assert notifications[0].user_id == recipient.id
    assert notifications[0].notification_type == "CHAT_MESSAGE_RECEIVED"
    assert notifications[0].data["message_id"] == str(message.id)
    sender_notifications = (
        (
            await test_session.execute(
                select(Notification).where(Notification.user_id == sender.id)
            )
        )
        .scalars()
        .all()
    )
    assert sender_notifications == []
    (
        duplicate_message,
        duplicate_notifications,
        duplicate_was_created,
    ) = await ChatRepository().save_message_with_notifications(
        room.id, sender.id, "Hello from the chat", client_message_id
    )
    assert duplicate_message.id == message.id
    assert duplicate_notifications == []
    assert duplicate_was_created is False


@pytest.mark.asyncio
async def test_successful_reviews_notify_the_relevant_tutor(test_session):
    tutor_user = User(
        id=uuid4(), full_name="Tutor", email="review-tutor@example.com", password="x"
    )
    tutor = Tutor(id=uuid4())
    student = Student(id=uuid4())
    service = Service(
        id=uuid4(),
        tutor_id=tutor.id,
        service_name="Python",
        date=date.today(),
        time=time(10),
        price=10,
        level=ServiceLevel.BEGINNER,
    )
    test_session.add_all(
        [
            tutor_user,
            tutor,
            student,
            service,
            UserRoleAssociation(
                user_id=tutor_user.id, role_id=uuid4(), tutor_id=tutor.id
            ),
        ]
    )
    await test_session.flush()

    await ReviewRepository().create_tutor_review(
        {
            "tutor_id": tutor.id,
            "student_id": student.id,
            "rating": 8,
            "comment": "Good",
        },
        session=test_session,
    )
    await ReviewRepository().create_service_review(
        {
            "service_id": service.id,
            "student_id": student.id,
            "rating": 9,
            "comment": "Great",
        },
        session=test_session,
    )

    notification_types = set(
        (
            await test_session.execute(
                select(Notification.notification_type).where(
                    Notification.user_id == tutor_user.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert notification_types == {"TUTOR_REVIEW_CREATED", "SERVICE_REVIEW_CREATED"}
