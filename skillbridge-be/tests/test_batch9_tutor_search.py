"""Tutor & search batch.

  * academic_program must survive registration and be filterable (item 14);
  * subject tags must be filterable alongside name and program (item 15);
  * hourly_price must be gone from the API and from sorting (item 16);
  * a free-text search combined with a filter and a sort must apply all
    three together, with pagination consistent with the filtered set
    (items 17, 18);
  * the service listing must carry the same enrolment count the service
    detail view derives from accepted bookings (item 19).
"""

import uuid as _uuid
from datetime import date, time, timedelta

import pytest

from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_bookings import ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.tutor_revisions import TutorRevision
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.api.repositories.auth.token import TokenRepository

from tests.test_batch6_audit import admin_factory  # noqa: F401
from tests.test_batch2_regressions import (  # noqa: F401  (fixtures)
    PASSWORD,
    _auth,
    client,
    student,
    world,
)


@pytest.fixture
def make_tutor(test_engine, world):
    """Create an approved, visible tutor that the public listing will return."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select

    async def _make(
        *,
        name: str,
        program: str = "Computer Science",
        bio: str = "general tutoring",
        tags: list[str] | None = None,
        created_at=None,
    ):
        factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            role = (
                await session.execute(select(Role).where(Role.slug == "tutor"))
            ).scalars().first()
            user = User(
                id=_uuid.uuid4(),
                full_name=name,
                email=f"{name.replace(' ', '.').lower()}@hs-fulda.de",
                phone="+4915100000",
                status="ACTIVE",
                has_registered=True,
                is_verified=True,
                password=TokenRepository.hash_password(PASSWORD),
            )
            session.add(user)
            tutor = Tutor(
                id=_uuid.uuid4(),
                academic_program=program,
                bio=bio,
                teaching_style="Interactive",
                is_visible=True,
                approval_status="ACCEPTED",
                accepting_requests=True,
                tags=tags or [],
                status="ACTIVE",
            )
            if created_at is not None:
                tutor.created_at = created_at
            session.add(tutor)
            await session.flush()
            session.add(
                UserRoleAssociation(
                    id=_uuid.uuid4(),
                    user_id=user.id,
                    role_id=role.id,
                    tutor_id=tutor.id,
                    status="ACTIVE",
                )
            )
            await session.commit()
            return str(tutor.id)

    return _make


# --------------------------------------------------------------------------
# Item 17 - search + filter + sort must combine
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_and_sort_apply_together(client, world, make_tutor):
    """Searching "zylotron" and sorting Newest returns the newest Python tutor."""
    from datetime import datetime, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await make_tutor(
        name="Old Zylo", bio="zylotron expert", created_at=base
    )
    newest = await make_tutor(
        name="New Zylo", bio="zylotron expert", created_at=base + timedelta(days=30)
    )
    await make_tutor(
        name="Newest Java", bio="java only", created_at=base + timedelta(days=60)
    )

    response = await client.get(
        "/api/v1/tutor/tutors/", params={"query": "zylotron", "sort": "newest"}
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    names = [item["user"]["full_name"] for item in data]
    # The Java tutor is newer but must be filtered out by the search term.
    assert "Newest Java" not in names
    assert data[0]["id"] == newest, names


@pytest.mark.asyncio
async def test_search_and_program_filter_apply_together(client, world, make_tutor):
    await make_tutor(name="Zy Maths", program="Mathematics", bio="zylotron")
    match = await make_tutor(name="Zy CompSci", program="Computer Science", bio="zylotron")

    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={"query": "zylotron", "academic_program": "Computer Science"},
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == [match], response.text


# --------------------------------------------------------------------------
# Item 18 - the count must match the filtered, paginated result set
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_total_matches_the_filtered_result_set(client, world, make_tutor):
    for index in range(3):
        await make_tutor(name=f"Zylo Tutor {index}", bio="zylotron")
    await make_tutor(name="Java Tutor", bio="java")

    response = await client.get(
        "/api/v1/tutor/tutors/", params={"query": "zylotron", "items_per_page": 100}
    )

    body = response.json()
    assert body["metadata"]["total_records"] == len(body["data"])


@pytest.mark.asyncio
async def test_pagination_walks_the_filtered_set_without_gaps(
    client, world, make_tutor
):
    for index in range(5):
        await make_tutor(name=f"Zylo Tutor {index}", bio="zylotron")

    first = await client.get(
        "/api/v1/tutor/tutors/",
        params={"query": "zylotron", "items_per_page": 2, "page": 1, "sort": "newest"},
    )
    second = await client.get(
        "/api/v1/tutor/tutors/",
        params={"query": "zylotron", "items_per_page": 2, "page": 2, "sort": "newest"},
    )

    assert first.json()["metadata"]["total_records"] == 5
    first_ids = [item["id"] for item in first.json()["data"]]
    second_ids = [item["id"] for item in second.json()["data"]]
    # A full page must actually be full, and pages must not overlap.
    assert len(first_ids) == 2, first_ids
    assert len(second_ids) == 2, second_ids
    assert not set(first_ids) & set(second_ids)


# --------------------------------------------------------------------------
# Item 15 - tags must be a first-class search filter
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tutors_can_be_filtered_by_tag(client, world, make_tutor):
    tagged = await make_tutor(name="Tagged Tutor", tags=["Django", "Python"])
    await make_tutor(name="Untagged Tutor", tags=["Cooking"])

    response = await client.get("/api/v1/tutor/tutors/", params={"tag": "Django"})

    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == [tagged]


@pytest.mark.asyncio
async def test_tag_filter_combines_with_search_and_program(client, world, make_tutor):
    match = await make_tutor(
        name="Combo Tutor", program="Computer Science", bio="zylotron", tags=["Django"]
    )
    await make_tutor(
        name="Wrong Program", program="Mathematics", bio="zylotron", tags=["Django"]
    )
    await make_tutor(
        name="Wrong Tag", program="Computer Science", bio="zylotron", tags=["Cooking"]
    )

    response = await client.get(
        "/api/v1/tutor/tutors/",
        params={
            "query": "zylotron",
            "academic_program": "Computer Science",
            "tag": "Django",
        },
    )

    ids = [item["id"] for item in response.json()["data"]]
    assert ids == [match], response.text


@pytest.mark.asyncio
async def test_tag_list_endpoint_returns_known_tags(client, world, make_tutor):
    await make_tutor(name="Tagged Tutor", tags=["Django", "Python"])

    response = await client.get("/api/v1/tutor/tags/")

    assert response.status_code == 200, response.text
    assert "Django" in response.json()["data"]


# --------------------------------------------------------------------------
# Item 16 - hourly price is gone
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tutor_payload_no_longer_carries_hourly_price(client, world):
    response = await client.get(
        "/api/v1/tutor/tutors/", params={"tutor_id": world["tutor"]}
    )

    assert response.status_code == 200
    assert "hourly_price" not in response.json()["data"][0]


@pytest.mark.asyncio
async def test_price_sorts_are_rejected(client, world):
    """Sorting tutors by price no longer means anything, so it must 400."""
    response = await client.get(
        "/api/v1/tutor/tutors/", params={"sort": "price:asc"}
    )
    assert response.status_code == 400, response.text


# --------------------------------------------------------------------------
# Item 14 - academic_program at registration
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registration_persists_the_academic_program(client, world, test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select

    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        role = (
            await session.execute(select(Role).where(Role.slug == "tutor"))
        ).scalars().first()
        role_id = str(role.id)

    response = await client.post(
        "/api/v1/user/register/",
        json={
            "full_name": "Program Tutor",
            "email": "program.tutor@hs-fulda.de",
            "phone": "+4915111111",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "role_id": role_id,
            "status": "ACTIVE",
            "has_registered": True,
            "is_verified": True,
            "bio": "I teach data science to first year students and beyond.",
            "teaching_style": "Worked examples and practice",
            "academic_program": "Data Science",
            "tags": ["Python"],
        },
    )

    assert response.status_code in (200, 201), response.text

    # Registration stages a PENDING tutor revision; the tutors row appears when
    # an admin approves it. Both must carry the program and the tags.
    async with factory() as session:
        revision = (
            await session.execute(
                select(TutorRevision).where(
                    TutorRevision.academic_program == "Data Science"
                )
            )
        ).scalars().first()
        assert revision is not None, "academic_program was not persisted"
        assert revision.tags == ["Python"]


@pytest.mark.asyncio
async def test_approval_carries_tags_onto_the_tutor(
    client, world, test_engine, admin_factory
):
    """Tags collected at registration must survive admin approval.

    They were stored on the revision and then dropped when the tutor row was
    created, so a tutor's subjects silently disappeared at approval time.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from skillbridge.api.repositories.tutor import TutorRepository
    from skillbridge.api.validators.service import RevisionType
    from skillbridge.utils.renderer import Status

    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        revision = TutorRevision(
            id=_uuid.uuid4(),
            tutor_id=None,
            academic_program="Physics",
            bio="I tutor mechanics and thermodynamics for first years.",
            teaching_style="Worked examples",
            tags=["Mechanics", "Thermodynamics"],
            is_visible=True,
            accepting_requests=True,
            approval_status=Status.PENDING,
            revision_type=RevisionType.CREATE,
            status="ACTIVE",
        )
        session.add(revision)
        await session.commit()
        revision_id = revision.id

    admin_id = await admin_factory()
    await TutorRepository().approve_tutor_revision(
        revision_id=revision_id, user_id=admin_id
    )

    async with factory() as session:
        tutor = (
            await session.execute(
                select(Tutor).where(Tutor.academic_program == "Physics")
            )
        ).scalars().first()
        assert tutor is not None
        assert tutor.tags == ["Mechanics", "Thermodynamics"]


# --------------------------------------------------------------------------
# Item 19 - one source of truth for the enrolment count
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_listing_reports_accepted_enrolments(
    client, world, student, test_engine
):
    """The listing count must equal what the detail view counts."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from datetime import datetime, timezone

    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        session.add(
            ServiceBooking(
                id=_uuid.uuid4(),
                service_id=_uuid.UUID(world["service"]),
                student_id=_uuid.UUID(student["student_id"]),
                status="ACCEPTED",
                scheduled_start_at=datetime.now(timezone.utc) + timedelta(days=5),
            )
        )
        await session.commit()

    listing = await client.get(
        "/api/v1/service/services/", params={"service_id": world["service"]}
    )
    assert listing.status_code == 200, listing.text
    service = listing.json()["data"][0]

    detail = await client.get(
        "/api/v1/service-booking/service-bookings/",
        params={"service_id": world["service"], "status": "ACCEPTED"},
        headers=_auth(world["tutor_user"]),
    )
    assert detail.status_code == 200, detail.text

    assert service["enrolled_students_count"] == len(detail.json()["data"]) == 1


@pytest.mark.asyncio
async def test_pending_bookings_do_not_count_as_enrolled(
    client, world, student, test_engine
):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from datetime import datetime, timezone

    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        session.add(
            ServiceBooking(
                id=_uuid.uuid4(),
                service_id=_uuid.UUID(world["service"]),
                student_id=_uuid.UUID(student["student_id"]),
                status="PENDING",
                scheduled_start_at=datetime.now(timezone.utc) + timedelta(days=5),
            )
        )
        await session.commit()

    listing = await client.get(
        "/api/v1/service/services/", params={"service_id": world["service"]}
    )
    assert listing.json()["data"][0]["enrolled_students_count"] == 0
