"""Regressions for the second QA batch (blockers).

  * a tutor viewing their own /tutors/ record must get their email and phone
    on `user`, since that is what the "my profile" page renders;
  * that must stay private to the owner - a browsing student must not receive
    another tutor's email/phone through the same field.
"""

import pytest

from tests.test_batch2_regressions import _auth, client, student, world  # noqa: F401


@pytest.mark.asyncio
async def test_tutor_sees_own_email_and_phone_on_their_profile(client, world):
    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["tutor"]},
        headers=_auth(world["tutor_user"]),
    )

    assert response.status_code == 200
    tutor = response.json()["data"][0]
    assert tutor["user"]["email"] == "tutor@hs-fulda.de"
    assert tutor["user"]["phone"] == "+4915100000"


@pytest.mark.asyncio
async def test_a_student_browsing_does_not_receive_the_tutors_email_or_phone(
    client, world, student
):
    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={"tutor_id": world["tutor"]},
        headers=_auth(student["user_id"]),
    )

    assert response.status_code == 200
    tutor = response.json()["data"][0]
    assert tutor["user"]["email"] is None
    assert tutor["user"]["phone"] is None
