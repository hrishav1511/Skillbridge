"""Filtering and sorting added for the batch 5 list work.

Also pins the sort-key contract: an unsupported `sort` is a bad request, not a
server fault. It used to raise AttributeError/ValueError out of the generic
sort builder and surface as an opaque 500.
"""

import pytest

from tests.test_batch2_regressions import (  # noqa: F401
    _auth, world, client, student, PASSWORD,
)


@pytest.mark.asyncio
async def test_rating_ascending_is_supported(client, world):
    for path in ("/api/v1/tutor/tutors/", "/api/v1/service/services/"):
        r = await client.get(path, params={"sort": "rating:asc"},
                             headers=_auth(world["tutor_user"]))
        assert r.status_code == 200, (path, r.text)


@pytest.mark.asyncio
async def test_earliest_session_sort_is_supported(client, world):
    r = await client.get("/api/v1/service/services/",
                         params={"sort": "date:asc"},
                         headers=_auth(world["tutor_user"]))
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_unknown_sort_is_a_bad_request_not_a_500(client, world):
    for sort in ("bogus:asc", "bogus", "date:sideways", ":asc"):
        r = await client.get("/api/v1/tutor/tutors/", params={"sort": sort},
                             headers=_auth(world["tutor_user"]))
        assert r.status_code == 400, (sort, r.status_code, r.text)
        assert "sort" in r.text.lower() or "supported" in r.text.lower(), r.text


@pytest.mark.asyncio
async def test_services_filter_by_tutor_academic_program(client, world):
    match = await client.get("/api/v1/service/services/",
                             params={"academic_program": "Computer"},
                             headers=_auth(world["tutor_user"]))
    assert match.status_code == 200, match.text
    assert len(match.json()["data"]) >= 1

    miss = await client.get("/api/v1/service/services/",
                            params={"academic_program": "Basket Weaving"},
                            headers=_auth(world["tutor_user"]))
    assert miss.status_code == 200, miss.text
    assert miss.json()["data"] == []


@pytest.mark.asyncio
async def test_academic_programs_endpoint_lists_distinct_options(client, world):
    r = await client.get("/api/v1/tutor/academic-programs/",
                         headers=_auth(world["tutor_user"]))
    assert r.status_code == 200, r.text
    print("\n[5.1 programs] %s" % r.json()["data"])
    assert "Computer Science" in r.json()["data"]


@pytest.mark.asyncio
async def test_bookings_list_reports_pagination(client, world, student):
    """The all-requests page pages through this endpoint.

    The repository always computed page counts, but the handler built its
    response without them, so `metadata` came back empty and there was nothing
    for a pager to read.
    """
    book = await client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"], "student_id": student["student_id"]},
        headers=_auth(student["user_id"]),
    )
    assert book.status_code == 201, book.text

    r = await client.get("/api/v1/service-booking/service-bookings/",
                         params={"items_per_page": 1},
                         headers=_auth(world["tutor_user"]))
    assert r.status_code == 200, r.text
    metadata = r.json()["metadata"]
    print("\n[5.2 bookings metadata] %s" % metadata)
    assert metadata.get("total_records", 0) >= 1
    assert metadata.get("current_page") == 1
    assert metadata.get("items_per_page") == 1


@pytest.mark.asyncio
async def test_bookings_list_filters_by_status(client, world, student):
    book = await client.post(
        "/api/v1/service-booking/create/",
        json={"service_id": world["service"], "student_id": student["student_id"]},
        headers=_auth(student["user_id"]),
    )
    assert book.status_code == 201, book.text

    pending = await client.get("/api/v1/service-booking/service-bookings/",
                               params={"status": "PENDING"},
                               headers=_auth(world["tutor_user"]))
    assert pending.status_code == 200
    assert len(pending.json()["data"]) == 1

    declined = await client.get("/api/v1/service-booking/service-bookings/",
                                params={"status": "DECLINED"},
                                headers=_auth(world["tutor_user"]))
    assert declined.status_code == 200
    assert declined.json()["data"] == []
