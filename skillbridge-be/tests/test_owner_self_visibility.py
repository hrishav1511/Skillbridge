"""A tutor must be able to read back their own profile and services.

Hiding a profile or pausing requests removes a tutor from the marketplace; it
must not hide the tutor from themselves. These tests also pin down that the
bypass is scoped to the caller's own rows, so it cannot be used to enumerate
profiles that are hidden from students.
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
    """Seed two tutors (one hidden, one paused) plus a student, on SQLite."""
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

        def make_user(email):
            user = User(id=uuid.uuid4(), full_name="Person", email=email,
                        phone="+4915100000", status="ACTIVE", has_registered=True,
                        is_verified=True,
                        password=TokenRepository.hash_password(PASSWORD))
            session.add(user)
            return user

        hidden_user = make_user("hidden@hs-fulda.de")
        paused_user = make_user("paused@hs-fulda.de")
        student_user = make_user("student@hs-fulda.de")
        await session.flush()

        student = Student(id=uuid.uuid4(), status="ACTIVE")
        session.add(student)

        def make_tutor(is_visible=True, accepting=True):
            tutor = Tutor(id=uuid.uuid4(), academic_program="CS", bio="bio",
                          phone="+49175000", teaching_style="Interactive",
                          approval_status="ACCEPTED", accepting_requests=accepting,
                          tags=["Python"], status="ACTIVE")
            session.add(tutor)
            return tutor

        hidden_tutor = make_tutor(is_visible=False)
        paused_tutor = make_tutor(accepting=False)
        await session.flush()

        session.add(UserRoleAssociation(id=uuid.uuid4(), user_id=hidden_user.id,
                                        role_id=roles["tutor"].id,
                                        tutor_id=hidden_tutor.id, status="ACTIVE"))
        session.add(UserRoleAssociation(id=uuid.uuid4(), user_id=paused_user.id,
                                        role_id=roles["tutor"].id,
                                        tutor_id=paused_tutor.id, status="ACTIVE"))
        session.add(UserRoleAssociation(id=uuid.uuid4(), user_id=student_user.id,
                                        role_id=roles["student"].id,
                                        student_id=student.id, status="ACTIVE"))
        session.add(Service(id=uuid.uuid4(), tutor_id=paused_tutor.id,
                            service_name="Paused Service", description="d",
                            date=date.today() + timedelta(days=5), time=time(10, 0),
                            end_time=time(11, 0), price=30, level="BEGINNER",
                            tags=["Python"], status="ACTIVE"))
        await session.commit()

        ids.update(
            hidden_tutor=str(hidden_tutor.id), paused_tutor=str(paused_tutor.id),
            hidden_user=hidden_user.id, paused_user=paused_user.id,
            student_user=student_user.id,
        )
    return ids


@pytest_asyncio.fixture
async def client(world):
    from skillbridge.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_hidden_tutor_can_read_their_own_profile(client, world):
    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["hidden_tutor"]},
        headers=_auth(world["hidden_user"]),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data) == 1, "a hidden tutor must still see their own profile"
    assert data[0]["id"] == world["hidden_tutor"]
    assert data[0]["is_visible"] is False


@pytest.mark.asyncio
async def test_hidden_tutor_is_still_invisible_to_a_student(client, world):
    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["hidden_tutor"]},
        headers=_auth(world["student_user"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_one_tutor_cannot_read_another_hidden_profile(client, world):
    """The bypass is scoped to the caller's own tutor row, not to tutors at large."""
    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["hidden_tutor"]},
        headers=_auth(world["paused_user"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_hidden_tutor_is_invisible_to_guests(client, world):
    response = await client.get(
        "/api/v1/tutor/tutors/", params={"tutor_id": world["hidden_tutor"]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_paused_tutor_can_still_list_their_own_services(client, world):
    response = await client.get(
        "/api/v1/service/services/",
        params={"tutor_id": world["paused_tutor"]},
        headers=_auth(world["paused_user"]),
    )
    assert response.status_code == 200, response.text
    names = [item["service_name"] for item in response.json()["data"]]
    assert names == ["Paused Service"]


@pytest.mark.asyncio
async def test_paused_tutor_services_stay_hidden_from_students(client, world):
    response = await client.get(
        "/api/v1/service/services/",
        params={"tutor_id": world["paused_tutor"]},
        headers=_auth(world["student_user"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []
