"""A service response must let a caller tell a tutor id from a user id.

ServiceOutput.tutor carries the tutor's *user* account, so ``tutor.id`` is a
user id while ``tutor_id`` is the tutors row. Reading one where the other was
meant is what left tutor detail pages and reviews pointing at nothing, so the
user id is also published under an unambiguous name.
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
        tutor_user = make_user(session, "it@hs-fulda.de")
        student_user = make_user(session, "is@hs-fulda.de")
        await session.flush()

        tutor = make_tutor(session)
        student = make_student(session)
        await session.flush()

        link(session, tutor_user, roles["tutor"], tutor=tutor)
        link(session, student_user, roles["student"], student=student)
        service = make_service(session, tutor, name="Identified")
        await session.commit()

        ids.update(
            tutor=str(tutor.id),
            tutor_user=tutor_user.id,
            service=str(service.id),
            student_user=student_user.id,
        )
    return ids


@pytest.mark.asyncio
async def test_service_reports_both_ids_distinctly(api_client, world):
    response = await api_client.get(
        "/api/v1/service/services/",
        params={"service_id": world["service"]},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 200, response.text
    service = response.json()["data"][0]

    assert service["tutor_id"] == world["tutor"]
    assert service["tutor_user_id"] == str(world["tutor_user"])
    assert service["tutor"]["id"] == str(world["tutor_user"])
    assert service["tutor_id"] != service["tutor_user_id"], (
        "the two ids must be distinguishable, otherwise the confusion is untestable"
    )


@pytest.mark.asyncio
async def test_a_guest_gets_neither_user_id(api_client, world):
    """The user id is identifying, so guests get no id at all - not a tutor id."""
    response = await api_client.get(
        "/api/v1/service/services/", params={"service_id": world["service"]}
    )
    assert response.status_code == 200, response.text
    service = response.json()["data"][0]
    assert service["tutor_user_id"] is None
    assert service["tutor"]["id"] is None


@pytest.mark.asyncio
async def test_a_guest_does_not_get_the_tutor_phone(api_client, world):
    response = await api_client.get(
        "/api/v1/tutor/tutors/", params={"tutor_id": world["tutor"]}
    )
    assert response.status_code == 200, response.text
    tutor = response.json()["data"][0]

    assert tutor["phone"] is None
    assert tutor["user"]["phone"] is None


@pytest.mark.asyncio
async def test_the_tutor_id_addresses_the_tutor_endpoint(api_client, world):
    """What the service calls tutor_id is what /tutor/tutors/ accepts."""
    response = await api_client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["tutor"]},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["data"]] == [world["tutor"]]


@pytest.mark.asyncio
async def test_the_user_id_does_not_address_the_tutor_endpoint(api_client, world):
    """Passing the user id where a tutor id belongs finds nothing - the bug's shape."""
    response = await api_client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": str(world["tutor_user"])},
        headers=auth_header(world["student_user"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []
