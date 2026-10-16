"""Regressions for the batch 1 QA reports, driven by the payloads from the bugs.

Each test pins the behaviour that was reported broken:
  * a long bio must fail as a named validation error, not as an opaque 500 from
    MySQL rejecting the old VARCHAR(255) column;
  * an out-of-range year must be refused by name so the form can show it;
  * chat timestamps must carry an explicit UTC offset, or the browser reads them
    as local time and renders every message at the wrong hour.
"""

import uuid
from datetime import date, time, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User

PASSWORD = "Passw0rd!x"


def _auth(user_id):
    return {
        "Authorization": "Bearer %s"
        % TokenRepository.create_tokens(str(user_id))["access_token"]
    }


@pytest_asyncio.fixture
async def world(test_engine, monkeypatch):
    from contextlib import asynccontextmanager
    import sys
    import types

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def patched_get_session():
        async with factory() as session:
            yield session

    for name, module in list(sys.modules.items()):
        if (
            name.startswith("skillbridge")
            and isinstance(module, types.ModuleType)
            and getattr(module, "get_session", None) is not None
        ):
            monkeypatch.setattr(module, "get_session", patched_get_session, raising=False)

    ids = {}
    async with factory() as session:
        roles = {}
        for slug in ("student", "tutor"):
            role = Role(id=uuid.uuid4(), slug=slug, title=slug, description=slug,
                        status="ACTIVE")
            session.add(role)
            roles[slug] = role
        await session.flush()

        tutor_user = User(id=uuid.uuid4(), full_name="Tutor Person",
                          email="tutor@hs-fulda.de", phone="+4915100000",
                          status="ACTIVE", has_registered=True, is_verified=True,
                          password=TokenRepository.hash_password(PASSWORD))
        session.add(tutor_user)
        await session.flush()

        tutor = Tutor(id=uuid.uuid4(), academic_program="Computer Science", bio="bio",
                      phone="+49175000", teaching_style="Interactive",
                      is_visible=True, approval_status="ACCEPTED",
                      accepting_requests=True, tags=["Python"], status="ACTIVE")
        session.add(tutor)
        await session.flush()

        session.add(UserRoleAssociation(id=uuid.uuid4(), user_id=tutor_user.id,
                                        role_id=roles["tutor"].id,
                                        tutor_id=tutor.id, status="ACTIVE"))
        svc = Service(id=uuid.uuid4(), tutor_id=tutor.id, service_name="Existing",
                      description="d", date=date.today() + timedelta(days=5),
                      time=time(13, 30), end_time=time(14, 30), price=30,
                      level="BEGINNER", tags=["Python"], status="ACTIVE")
        session.add(svc)
        await session.commit()

        ids.update(tutor=str(tutor.id), tutor_user=tutor_user.id,
                   service=str(svc.id))
    return ids


@pytest_asyncio.fixture
async def client(world):
    from skillbridge.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_user(test_engine, world):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    import uuid as _uuid

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        role = Role(id=_uuid.uuid4(), slug="admin", title="admin",
                    description="admin", status="ACTIVE")
        session.add(role)
        user = User(id=_uuid.uuid4(), full_name="Admin", email="admin@hs-fulda.de",
                    phone="+491", status="ACTIVE", has_registered=True,
                    is_verified=True,
                    password=TokenRepository.hash_password(PASSWORD))
        session.add(user)
        await session.flush()
        session.add(UserRoleAssociation(id=_uuid.uuid4(), user_id=user.id,
                                        role_id=role.id, status="ACTIVE"))
        await session.commit()
        return user.id


@pytest.mark.asyncio
async def test_long_bio_is_a_named_validation_error(client, world):
    r = await client.put("/api/v1/tutor/%s/" % world["tutor"],
                         json={"bio": "x" * 2500},
                         headers=_auth(world["tutor_user"]))
    print("\n[1.1 long bio] status=%s body=%s" % (r.status_code, r.text[:300]))
    assert r.status_code == 422
    assert "bio" in r.text

    ok = await client.put("/api/v1/tutor/%s/" % world["tutor"],
                          json={"bio": "y" * 1500},
                          headers=_auth(world["tutor_user"]))
    print("\n[1.1 1500-char bio] status=%s" % ok.status_code)
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_out_of_range_year_is_refused_by_name(client, world):
    base = {
        "tutor_id": world["tutor"], "service_name": "QA Service", "description": "A valid description",
        "price": "50", "level": "BEGINNER", "joining_link": "https://zoom.us/x",
        "end_time": "15:34:00",
    }
    bad = await client.post("/api/v1/service/create/",
                            data=dict(base, date="23423-03-24", time="14:34:00"),
                            headers=_auth(world["tutor_user"]))
    print("\n[1.3 bad date] status=%s body=%s" % (bad.status_code, bad.text[:250]))
    assert bad.status_code == 422
    assert bad.json()["detail"][0]["field"] == "date"

    good = await client.post(
        "/api/v1/service/create/",
        data=dict(base, date=str(date.today() + timedelta(days=10)), time="14:34:00"),
        headers=_auth(world["tutor_user"]))
    print("\n[1.3 good] status=%s" % good.status_code)
    assert good.status_code == 201


@pytest.mark.asyncio
async def test_chat_timestamps_carry_utc_offset(client, world, admin_user):
    from skillbridge.api.repositories.chat import ChatRepository

    room = await client.post("/api/v1/chat/rooms/direct/",
                             params={"target_user_id": str(world["tutor_user"])},
                             headers=_auth(admin_user))
    room_id = room.json()["chat_room_id"]

    repo = ChatRepository()
    import uuid as _uuid
    await repo.save_message_with_notifications(
        chat_room_id=_uuid.UUID(room_id), sender_id=admin_user,
        content="hello tutor", client_message_id=str(_uuid.uuid4()))

    msgs = await client.get("/api/v1/chat/rooms/%s/messages/?limit=10" % room_id,
                            headers=_auth(admin_user))
    created = msgs.json()["messages"][0]["created_at"]
    print("\n[1.7 history created_at] %r" % created)
    assert created.endswith("+00:00"), created

    rooms = await client.get("/api/v1/chat/rooms/", headers=_auth(admin_user))
    last = rooms.json()[0]["last_message"]["created_at"]
    print("\n[1.7 room list created_at] %r" % last)
    assert last.endswith("+00:00"), last
