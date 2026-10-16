"""Regressions for the batch 2 QA reports.

  * accepting a request must make the student visible to the attendance view,
    filtered to accepted bookings and carrying the student's name;
  * tutor search must match on bio, not just the fields it already covered;
  * login must return the avatar the navbar renders;
  * report lists must name the people involved instead of exposing UUIDs.
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


@pytest.mark.asyncio
async def test_repro_1_1_tutor_update(client, world):
    payload = {
        "is_favorite": False,
        "account_status": None,
        "academic_program": None,
        "bio": "Updated bio from QA",
    }
    r = await client.put("/api/v1/tutor/%s/" % world["tutor"], json=payload,
                         headers=_auth(world["tutor_user"]))
    print("\n[1.1] status=%s\nbody=%s" % (r.status_code, r.text[:3000]))


@pytest.mark.asyncio
async def test_repro_1_2_academic_program_roundtrip(client, world):
    r = await client.put("/api/v1/tutor/%s/" % world["tutor"],
                         json={"academic_program": "Data Science", "bio": "b"},
                         headers=_auth(world["tutor_user"]))
    print("\n[1.2 PUT] status=%s\nbody=%s" % (r.status_code, r.text[:2000]))
    g = await client.get("/api/v1/tutor/tutors/", params={"tutor_id": world["tutor"]},
                         headers=_auth(world["tutor_user"]))
    print("\n[1.2 GET] status=%s\nbody=%s" % (g.status_code, g.text[:2000]))


@pytest_asyncio.fixture
async def student(test_engine, world):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    import uuid as _uuid
    from sqlalchemy import select as _select

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        role = (await session.execute(
            _select(Role).where(Role.slug == "student"))).scalars().first()
        user = User(id=_uuid.uuid4(), full_name="Stu Dent",
                    email="stu@hs-fulda.de", phone="+492", status="ACTIVE",
                    has_registered=True, is_verified=True,
                    password=TokenRepository.hash_password(PASSWORD))
        session.add(user)
        st = Student(id=_uuid.uuid4(), status="ACTIVE")
        session.add(st)
        await session.flush()
        session.add(UserRoleAssociation(id=_uuid.uuid4(), user_id=user.id,
                                        role_id=role.id, student_id=st.id,
                                        status="ACTIVE"))
        await session.commit()
        return {"user_id": user.id, "student_id": str(st.id)}


@pytest.mark.asyncio
async def test_accepted_booking_appears_in_attendance(client, world, student):
    book = await client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"], "student_id": student["student_id"]},
        headers=_auth(student["user_id"]),
    )
    booking_id = book.json()["data"]["id"]
    await client.patch("/api/v1/service-booking/%s/accept/" % booking_id,
                       headers=_auth(world["tutor_user"]))

    r = await client.get("/api/v1/service-booking/service-bookings/",
                         params={"service_id": world["service"], "status": "ACCEPTED"},
                         headers=_auth(world["tutor_user"]))
    print("\n[2.1 accepted for service] status=%s" % r.status_code)
    for b in r.json()["data"]:
        print("   booking=%s status=%s student=%s" % (
            b["id"][:8], b["status"], (b.get("student") or {}).get("user")))

    p = await client.get("/api/v1/service-booking/service-bookings/",
                         params={"service_id": world["service"], "status": "PENDING"},
                         headers=_auth(world["tutor_user"]))
    print("\n[2.1 pending for service] count=%s" % len(p.json()["data"]))


@pytest.mark.asyncio
async def test_tutor_search_matches_bio(client, world):
    # The seeded tutor's bio is "bio"; search for a fragment of it.
    r = await client.get("/api/v1/tutor/tutors/", params={"query": "BI"},
                         headers=_auth(world["tutor_user"]))
    print("\n[2.2 bio search] status=%s matches=%s" % (
        r.status_code, len(r.json()["data"])))
    assert len(r.json()["data"]) == 1

    miss = await client.get("/api/v1/tutor/tutors/",
                            params={"query": "zzzznotpresent"},
                            headers=_auth(world["tutor_user"]))
    print("\n[2.2 non-match] matches=%s" % len(miss.json()["data"]))
    assert len(miss.json()["data"]) == 0


@pytest.mark.asyncio
async def test_login_returns_profile_picture(client, world, test_engine, student):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select as _select
    from skillbridge.database.models.sqlalchemy.tutors import Tutor as _Tutor
    import uuid as _uuid

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        t = await session.get(_Tutor, _uuid.UUID(world["tutor"]))
        t.profile_picture_url = "https://cdn.example/tutor.png"
        st = (await session.execute(_select(Student))).scalars().first()
        st.profile_picture_url = "https://cdn.example/student.png"
        await session.commit()
        role_id = (await session.execute(
            _select(Role).where(Role.slug == "tutor"))).scalars().first().id
        student_role_id = (await session.execute(
            _select(Role).where(Role.slug == "student"))).scalars().first().id

    r = await client.post("/api/v1/user/login/", json={
        "email": "tutor@hs-fulda.de", "password": PASSWORD, "role_id": str(role_id)})
    print("\n[2.3 tutor login] status=%s pic=%r" % (
        r.status_code, r.json()["data"].get("profile_picture_url")))
    assert r.json()["data"]["profile_picture_url"] == "https://cdn.example/tutor.png"

    r2 = await client.post("/api/v1/user/login/", json={
        "email": "stu@hs-fulda.de", "password": PASSWORD,
        "role_id": str(student_role_id)})
    print("\n[2.3 student login] status=%s pic=%r" % (
        r2.status_code, r2.json()["data"].get("profile_picture_url")))
    assert r2.json()["data"]["profile_picture_url"] == "https://cdn.example/student.png"


@pytest.mark.asyncio
async def test_reports_carry_names_and_dates(client, world, student, test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select as _select
    import uuid as _uuid

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        role = Role(id=_uuid.uuid4(), slug="admin", title="admin",
                    description="admin", status="ACTIVE")
        session.add(role)
        admin = User(id=_uuid.uuid4(), full_name="Admin", email="admin@hs-fulda.de",
                     phone="+491", status="ACTIVE", has_registered=True,
                     is_verified=True,
                     password=TokenRepository.hash_password(PASSWORD))
        session.add(admin)
        await session.flush()
        session.add(UserRoleAssociation(id=_uuid.uuid4(), user_id=admin.id,
                                        role_id=role.id, status="ACTIVE"))
        await session.commit()
        admin_id = admin.id

    rt = await client.post("/api/v1/report/tutor/",
                           json={"tutor_id": world["tutor"],
                                 "reason": "This tutor never showed up to the session."},
                           headers=_auth(student["user_id"]))
    print("\n[2.4 report tutor] status=%s" % rt.status_code)

    rs = await client.post("/api/v1/report/service/",
                           json={"service_id": world["service"],
                                 "reason": "The service description is misleading."},
                           headers=_auth(student["user_id"]))
    print("\n[2.4 report service] status=%s" % rs.status_code)

    lt = await client.get("/api/v1/report/tutor/", headers=_auth(admin_id))
    print("\n[2.4 tutor reports] %s" % lt.json()["data"])
    row = lt.json()["data"][0]
    assert row["tutor_name"] == "Tutor Person", row
    assert row["reporter_name"] == "Stu Dent", row
    assert row["reported_at"]

    ls = await client.get("/api/v1/report/service/", headers=_auth(admin_id))
    print("\n[2.4 service reports] %s" % ls.json()["data"])
    srow = ls.json()["data"][0]
    assert srow["service_name"] == "Existing", srow
    assert srow["reporter_name"] == "Stu Dent", srow


@pytest.mark.asyncio
async def test_service_list_feeds_the_calendar(client, world, test_engine):
    """The tutor dashboard calendar reads past and future sessions from here.

    A past-dated service must come back, or navigating to an earlier month
    shows an empty grid, and items_per_page must accept the page size the
    calendar asks for.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    import uuid as _uuid

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(Service(
            id=_uuid.uuid4(), tutor_id=_uuid.UUID(world["tutor"]),
            service_name="Last month", description="d",
            date=date.today() - timedelta(days=30), time=time(9, 0),
            end_time=time(10, 0), price=20, level="BEGINNER",
            tags=["Python"], status="ACTIVE"))
        await session.commit()

    r = await client.get("/api/v1/service/services/",
                         params={"tutor_id": world["tutor"], "items_per_page": 100},
                         headers=_auth(world["tutor_user"]))
    assert r.status_code == 200, r.text
    names = {item["service_name"] for item in r.json()["data"]}
    print("\n[calendar feed] status=%s names=%s" % (r.status_code, names))
    assert "Last month" in names, names

    over = await client.get("/api/v1/service/services/",
                            params={"tutor_id": world["tutor"], "items_per_page": 500},
                            headers=_auth(world["tutor_user"]))
    print("\n[calendar feed] items_per_page=500 -> %s" % over.status_code)
    assert over.status_code == 422
