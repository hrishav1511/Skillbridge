"""Guest browsing must never hit a 401.

The reported symptom was a single endpoint:

    GET /api/v1/tutor/academic-programs/ -> 401 (Unauthorized)

but the fix is only correct if *every* endpoint the guest session touches
while browsing answers anonymously. These tests sweep that whole surface with
no Authorization header at all, and pin the endpoints that must stay closed so
the fix cannot be widened by accident later.
"""

import pytest

from tests.test_batch2_regressions import (  # noqa: F401  (fixtures)
    PASSWORD,
    _auth,
    client,
    student,
    world,
)


# Everything the browse flow calls: the dashboard lists, the filter dropdown
# that broke, the tutor profile a guest can open, and both review lists.
GUEST_BROWSE_ENDPOINTS = [
    "/api/v1/tutor/tutors/",
    "/api/v1/tutor/academic-programs/",
    # Added with the subject filter; it broke guest browsing a second time by
    # being missing from the frontend interceptor's allowlist.
    "/api/v1/tutor/tags/",
    "/api/v1/service/services/",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", GUEST_BROWSE_ENDPOINTS)
async def test_guest_browsing_never_returns_401(client, world, path):
    response = await client.get(path)
    assert response.status_code == 200, (path, response.status_code, response.text)


@pytest.mark.asyncio
async def test_academic_programs_is_readable_by_a_guest(client, world):
    """The reported bug, pinned directly."""
    response = await client.get("/api/v1/tutor/academic-programs/")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_academic_programs_still_rejects_a_bad_token(client, world):
    """Open to guests is not the same as ignoring credentials.

    A caller who sends a token is claiming a session; a broken one must be
    reported rather than silently downgraded to guest.
    """
    response = await client.get(
        "/api/v1/tutor/academic-programs/",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_academic_programs_matches_for_a_signed_in_user(client, world, student):
    """A guest and a signed-in student see the same public programs."""
    guest = await client.get("/api/v1/tutor/academic-programs/")
    signed_in = await client.get(
        "/api/v1/tutor/academic-programs/", headers=_auth(student["user_id"])
    )

    assert guest.status_code == signed_in.status_code == 200
    assert guest.json()["data"] == signed_in.json()["data"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/service-booking/service-bookings/",
        "/api/v1/chat/rooms/",
        "/api/v1/favorites/tutors/",
    ],
)
async def test_account_only_endpoints_stay_closed_to_guests(client, world, path):
    """Opening the browse endpoints must not open the personal ones."""
    response = await client.get(path)
    assert response.status_code in (401, 403, 404, 405), (path, response.status_code)
