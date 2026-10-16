"""Deactivating a tutor removes them from the marketplace, not from their account.

Deactivation used to flip User.status, which is the same switch authentication
reads, so a "deactivated" tutor was locked out entirely. The state now lives on
the Tutor row: the tutor keeps their login and their own data, while browsing,
search, booking and chat all refuse them.
"""

import pytest
import pytest_asyncio

from tests.conftest import auth_header
from tests.factories import (
    link,
    make_service,
    make_student,
    make_tutor,
    make_user,
    seed_roles,
)


@pytest_asyncio.fixture
async def world(session_factory):
    ids = {}
    async with session_factory() as session:
        roles = await seed_roles(session)
        tutor_user = make_user(session, "dt@hs-fulda.de")
        student_user = make_user(session, "ds@hs-fulda.de")
        admin_user = make_user(session, "da@hs-fulda.de")
        await session.flush()

        tutor = make_tutor(session, status="INACTIVE")
        student = make_student(session)
        await session.flush()

        link(session, tutor_user, roles["tutor"], tutor=tutor)
        link(session, student_user, roles["student"], student=student)
        link(session, admin_user, roles["admin"])
        service = make_service(session, tutor, name="Deactivated Service")
        await session.commit()

        ids.update(
            tutor=str(tutor.id),
            service=str(service.id),
            tutor_user=tutor_user.id,
            student_user=student_user.id,
            admin_user=admin_user.id,
        )
    return ids


@pytest.mark.asyncio
async def test_deactivated_tutor_is_not_listed_to_students(api_client, world):
    response = await api_client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["tutor"]},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_deactivated_tutor_is_not_searchable(api_client, world):
    response = await api_client.get(
        "/api/v1/tutor/tutors/", params={"query": "CS"}
    )
    assert response.status_code == 200, response.text
    assert world["tutor"] not in [item["id"] for item in response.json()["data"]]


@pytest.mark.asyncio
async def test_deactivated_tutor_cannot_be_booked(api_client, world):
    response = await api_client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"]},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_deactivated_tutor_cannot_be_messaged(api_client, world):
    response = await api_client.post(
        "/api/v1/chat/rooms/direct/",
        params={"target_user_id": str(world["tutor_user"])},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_deactivated_tutor_still_sees_their_own_profile(api_client, world):
    response = await api_client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["tutor"]},
        headers=auth_header(world["tutor_user"]),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == world["tutor"]


@pytest.mark.asyncio
async def test_admin_status_toggle_reports_the_tutor_row(api_client, world):
    response = await api_client.patch(
        f"/api/v1/admin/tutors/{world['tutor']}/status/",
        json={"status": "ACTIVE"},
        headers=auth_header(world["admin_user"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "tutor_id": world["tutor"],
        "status": "ACTIVE",
    }
