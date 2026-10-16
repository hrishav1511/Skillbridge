"""Backend support for the admin moderation batch.

  * the pending-approval payload must carry the service's images and videos,
    so the admin can review the media before approving (item 10);
  * review reports must name the reporter, like tutor/service reports already
    do, instead of handing the panel a bare UUID (item 11);
  * admins need to list every service and disable one directly, not only by
    way of a report, and a disabled service must drop out of the student
    listing (item 13).
"""

import uuid as _uuid
from datetime import date, time, timedelta

import pytest

from skillbridge.database.models.sqlalchemy.service_revisions import ServiceRevision
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.utils.renderer import Status

from tests.test_batch2_regressions import (  # noqa: F401  (fixtures)
    PASSWORD,
    _auth,
    client,
    student,
    world,
)
from tests.test_batch6_audit import admin_factory  # noqa: F401


IMAGES = ["https://cdn.example.com/a.png", "https://cdn.example.com/b.png"]
VIDEOS = ["https://cdn.example.com/clip.mp4"]


@pytest.fixture
def pending_revision(test_engine, world):
    """A PENDING service revision carrying images and a video."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    async def _make():
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            revision = ServiceRevision(
                id=_uuid.uuid4(),
                tutor_id=_uuid.UUID(world["tutor"]),
                service_name="Media heavy service",
                description="With pictures",
                date=date.today() + timedelta(days=3),
                time=time(10, 0),
                end_time=time(11, 0),
                price=40,
                level="BEGINNER",
                revision_type="CREATE",
                approval_status=Status.PENDING,
                image_urls=IMAGES,
                video_urls=VIDEOS,
                video_url=VIDEOS[0],
                tags=["Python"],
                status="ACTIVE",
            )
            session.add(revision)
            await session.commit()
            return str(revision.id)

    return _make


# --------------------------------------------------------------------------
# Item 10 - media must reach the approval modal
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_revision_payload_carries_service_media(
    client, world, admin_factory, pending_revision
):
    await pending_revision()
    admin_id = await admin_factory()

    response = await client.get(
        "/api/v1/admin/service_revisions/pending/", headers=_auth(admin_id)
    )

    assert response.status_code == 200
    revision = next(
        item
        for item in response.json()["data"]
        if item["service_name"] == "Media heavy service"
    )
    assert revision["image_urls"] == IMAGES
    assert revision["video_urls"] == VIDEOS
    assert revision["video_url"] == VIDEOS[0]


# --------------------------------------------------------------------------
# Item 11 - review reports need the reporter's name
# --------------------------------------------------------------------------


@pytest.fixture
def seeded_review(test_engine, world, student):
    """A tutor review, inserted directly.

    Posting one through the API needs a completed booking first; that
    eligibility rule is covered elsewhere and is not what these tests are
    about.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    async def _make():
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            review = TutorReview(
                id=_uuid.uuid4(),
                tutor_id=_uuid.UUID(world["tutor"]),
                student_id=_uuid.UUID(student["student_id"]),
                rating=1,
                comment="Abusive language in the session.",
                status="ACTIVE",
            )
            session.add(review)
            await session.commit()
            return str(review.id)

    return _make


@pytest.mark.asyncio
async def test_review_reports_name_the_reporter(
    client, world, student, admin_factory, seeded_review
):
    review_id = await seeded_review()
    reported = await client.post(
        f"/api/v1/report/review/tutor/{review_id}/",
        json={"reason": "This review contains personal abuse and should go."},
        headers=_auth(student["user_id"]),
    )
    assert reported.status_code in (200, 201), reported.text

    admin_id = await admin_factory()
    response = await client.get("/api/v1/report/review/", headers=_auth(admin_id))

    assert response.status_code == 200
    report = response.json()["data"][0]
    # The panel renders a "Reported by" column; a raw UUID is not a name.
    assert report["reporter_name"] == "Stu Dent"


# --------------------------------------------------------------------------
# Item 13 - admin service list and direct disable
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_list_every_service(client, world, admin_factory):
    admin_id = await admin_factory()

    response = await client.get("/api/v1/admin/services/", headers=_auth(admin_id))

    assert response.status_code == 200
    names = [item["service_name"] for item in response.json()["data"]]
    assert "Existing" in names


@pytest.mark.asyncio
async def test_admin_service_list_is_admin_only(client, world, student):
    response = await client.get(
        "/api/v1/admin/services/", headers=_auth(student["user_id"])
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_disabling_a_service_hides_it_from_students(
    client, world, student, admin_factory
):
    admin_id = await admin_factory()

    visible_before = await client.get("/api/v1/service/services/")
    assert world["service"] in [item["id"] for item in visible_before.json()["data"]]

    disabled = await client.patch(
        f"/api/v1/admin/services/{world['service']}/status/",
        json={"status": "INACTIVE"},
        headers=_auth(admin_id),
    )
    assert disabled.status_code == 200, disabled.text

    visible_after = await client.get("/api/v1/service/services/")
    assert world["service"] not in [item["id"] for item in visible_after.json()["data"]]


@pytest.mark.asyncio
async def test_a_disabled_service_can_be_re_enabled(client, world, admin_factory):
    admin_id = await admin_factory()

    await client.patch(
        f"/api/v1/admin/services/{world['service']}/status/",
        json={"status": "INACTIVE"},
        headers=_auth(admin_id),
    )
    restored = await client.patch(
        f"/api/v1/admin/services/{world['service']}/status/",
        json={"status": "ACTIVE"},
        headers=_auth(admin_id),
    )

    assert restored.status_code == 200
    visible = await client.get("/api/v1/service/services/")
    assert world["service"] in [item["id"] for item in visible.json()["data"]]


@pytest.mark.asyncio
async def test_service_status_rejects_an_unknown_value(client, world, admin_factory):
    admin_id = await admin_factory()

    response = await client.patch(
        f"/api/v1/admin/services/{world['service']}/status/",
        json={"status": "BANISHED"},
        headers=_auth(admin_id),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_students_cannot_disable_a_service(client, world, student):
    response = await client.patch(
        f"/api/v1/admin/services/{world['service']}/status/",
        json={"status": "INACTIVE"},
        headers=_auth(student["user_id"]),
    )
    assert response.status_code == 403
