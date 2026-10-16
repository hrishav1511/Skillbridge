"""POST /v1/service-booking/create/ must actually create a booking.

The endpoint handed BaseValidator a plain dict, which is not a pydantic model,
so validation blew up before the repository was ever reached and every booking
attempt failed. student_id is server-derived from the access token; a client
that supplies someone else's id is refused rather than silently corrected.
"""

import pytest
import pytest_asyncio

from tests.conftest import auth_header
from tests.factories import link, make_service, make_student, make_tutor, make_user, seed_roles


@pytest_asyncio.fixture
async def world(session_factory):
    ids = {}
    async with session_factory() as session:
        roles = await seed_roles(session)
        tutor_user = make_user(session, "bt@hs-fulda.de")
        student_user = make_user(session, "bs@hs-fulda.de")
        other_student_user = make_user(session, "bs2@hs-fulda.de")
        await session.flush()

        tutor = make_tutor(session)
        student = make_student(session)
        other_student = make_student(session)
        await session.flush()

        link(session, tutor_user, roles["tutor"], tutor=tutor)
        link(session, student_user, roles["student"], student=student)
        link(session, other_student_user, roles["student"], student=other_student)
        service = make_service(session, tutor, name="Bookable")
        await session.commit()

        ids.update(
            service=str(service.id),
            student=str(student.id),
            other_student=str(other_student.id),
            student_user=student_user.id,
            tutor_user=tutor_user.id,
        )
    return ids


@pytest.mark.asyncio
async def test_student_can_book_a_service(api_client, world):
    response = await api_client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"]},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["service_id"] == world["service"]
    assert data["student_id"] == world["student"]
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_booking_uses_the_token_student_not_the_payload(api_client, world):
    """A supplied student_id that is not the caller's is refused, not honoured."""
    response = await api_client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"], "student_id": world["other_student"]},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_a_tutor_cannot_book(api_client, world):
    response = await api_client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"]},
        headers=auth_header(world["tutor_user"]),
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_unknown_service_is_a_404_not_a_500(api_client, world):
    import uuid

    response = await api_client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": str(uuid.uuid4())},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_the_orphan_service_path_is_gone(api_client):
    from skillbridge.app import app

    paths = {route.path for route in app.routes}
    assert "/v1/service/create/booking/" not in paths
