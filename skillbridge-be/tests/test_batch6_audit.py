"""Audit of the user-reporting feature against the batch 6 specification.

Exercises the whole surface end to end so the audit rests on observed
behaviour rather than on reading the handlers.
"""

import uuid as _uuid

import pytest

from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User

from tests.test_batch2_regressions import (  # noqa: F401
    _auth, world, client, student, PASSWORD,
)


@pytest.fixture
def admin_factory(test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    async def _make():
        factory = async_sessionmaker(test_engine, class_=AsyncSession,
                                     expire_on_commit=False)
        async with factory() as session:
            role = Role(id=_uuid.uuid4(), slug="admin", title="admin",
                        description="admin", status="ACTIVE")
            session.add(role)
            user = User(id=_uuid.uuid4(), full_name="Admin",
                        email="admin@hs-fulda.de", phone="+491", status="ACTIVE",
                        has_registered=True, is_verified=True,
                        password=TokenRepository.hash_password(PASSWORD))
            session.add(user)
            await session.flush()
            session.add(UserRoleAssociation(id=_uuid.uuid4(), user_id=user.id,
                                            role_id=role.id, status="ACTIVE"))
            await session.commit()
            return user.id
    return _make


async def _report(client, world, student, kind="tutor"):
    if kind == "tutor":
        body = {"tutor_id": world["tutor"],
                "reason": "This tutor did not attend the booked session."}
    else:
        body = {"service_id": world["service"],
                "reason": "The service description does not match the session."}
    r = await client.post(f"/api/v1/report/{kind}/", json=body,
                          headers=_auth(student["user_id"]))
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


@pytest.mark.asyncio
async def test_students_can_create_both_report_types(client, world, student):
    assert await _report(client, world, student, "tutor")
    assert await _report(client, world, student, "service")


@pytest.mark.asyncio
async def test_report_listing_is_admin_only(client, world, student, admin_factory):
    await _report(client, world, student, "tutor")
    await _report(client, world, student, "service")

    for kind in ("tutor", "service"):
        for actor in (student["user_id"], world["tutor_user"]):
            r = await client.get(f"/api/v1/report/{kind}/", headers=_auth(actor))
            assert r.status_code == 403, (kind, r.status_code, r.text)

        anon = await client.get(f"/api/v1/report/{kind}/")
        assert anon.status_code in (401, 403), (kind, anon.status_code)

    admin_id = await admin_factory()
    for kind in ("tutor", "service"):
        ok = await client.get(f"/api/v1/report/{kind}/", headers=_auth(admin_id))
        assert ok.status_code == 200, (kind, ok.text)


@pytest.mark.asyncio
async def test_admin_actions_are_admin_only(client, world, student, admin_factory):
    tutor_report = await _report(client, world, student, "tutor")
    service_report = await _report(client, world, student, "service")

    for path in (f"/api/v1/report/tutor/{tutor_report}/disable/",
                 f"/api/v1/report/service/{service_report}/disable/"):
        r = await client.patch(path, headers=_auth(student["user_id"]))
        assert r.status_code == 403, (path, r.status_code)

    for path in (f"/api/v1/report/tutor/{tutor_report}/",
                 f"/api/v1/report/service/{service_report}/"):
        r = await client.delete(path, headers=_auth(student["user_id"]))
        assert r.status_code == 403, (path, r.status_code)


@pytest.mark.asyncio
async def test_disable_tutor_deactivates_and_clears_the_report(
    client, world, student, admin_factory
):
    report_id = await _report(client, world, student, "tutor")
    admin_id = await admin_factory()

    r = await client.patch(f"/api/v1/report/tutor/{report_id}/disable/",
                           headers=_auth(admin_id))
    assert r.status_code == 200, r.text
    print("\n[6 disable tutor] %s" % r.text[:200])
    assert r.json()["data"]["status"] == "INACTIVE"

    remaining = await client.get("/api/v1/report/tutor/", headers=_auth(admin_id))
    assert remaining.json()["data"] == []


@pytest.mark.asyncio
async def test_disable_service_deactivates_and_clears_the_report(
    client, world, student, admin_factory
):
    report_id = await _report(client, world, student, "service")
    admin_id = await admin_factory()

    r = await client.patch(f"/api/v1/report/service/{report_id}/disable/",
                           headers=_auth(admin_id))
    assert r.status_code == 200, r.text
    print("\n[6 disable service] %s" % r.text[:200])
    assert r.json()["data"]["status"] == "INACTIVE"

    remaining = await client.get("/api/v1/report/service/", headers=_auth(admin_id))
    assert remaining.json()["data"] == []


@pytest.mark.asyncio
async def test_discard_removes_the_report_without_touching_the_entity(
    client, world, student, admin_factory
):
    admin_id = await admin_factory()

    tutor_report = await _report(client, world, student, "tutor")
    d = await client.delete(f"/api/v1/report/tutor/{tutor_report}/",
                            headers=_auth(admin_id))
    assert d.status_code == 200, d.text
    assert (await client.get("/api/v1/report/tutor/",
                             headers=_auth(admin_id))).json()["data"] == []

    # The tutor must still be listed; discarding is "no action taken".
    tutors = await client.get("/api/v1/tutor/tutors/",
                              params={"tutor_id": world["tutor"]},
                              headers=_auth(admin_id))
    assert len(tutors.json()["data"]) == 1

    service_report = await _report(client, world, student, "service")
    d2 = await client.delete(f"/api/v1/report/service/{service_report}/",
                             headers=_auth(admin_id))
    assert d2.status_code == 200, d2.text


@pytest.mark.asyncio
async def test_reason_is_required_and_bounded(client, world, student):
    for reason in ("", "   ", "too short"):
        r = await client.post("/api/v1/report/tutor/",
                              json={"tutor_id": world["tutor"], "reason": reason},
                              headers=_auth(student["user_id"]))
        assert r.status_code == 422, (reason, r.status_code)

    long = await client.post("/api/v1/report/tutor/",
                             json={"tutor_id": world["tutor"], "reason": "x" * 1001},
                             headers=_auth(student["user_id"]))
    assert long.status_code == 422


@pytest.mark.asyncio
async def test_tutors_cannot_report(client, world, student):
    r = await client.post("/api/v1/report/tutor/",
                          json={"tutor_id": world["tutor"],
                                "reason": "A tutor should not be able to report."},
                          headers=_auth(world["tutor_user"]))
    print("\n[6 tutor reporting] status=%s" % r.status_code)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_reports_are_currently_unconstrained(
    client, world, student, admin_factory
):
    """Documents current behaviour: the same student can report repeatedly.

    Review reports guard against this with a unique constraint; tutor and
    service reports do not, so one student can fill the admin queue.
    """
    for _ in range(3):
        await _report(client, world, student, "tutor")

    admin_id = await admin_factory()
    listed = await client.get("/api/v1/report/tutor/", headers=_auth(admin_id))
    print("\n[6 duplicate reports from one student] count=%s"
          % len(listed.json()["data"]))
    assert len(listed.json()["data"]) == 3
