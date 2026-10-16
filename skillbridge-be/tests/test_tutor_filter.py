import pytest

from skillbridge.api.filters.tutor import TutorSearchFilter
from skillbridge.api.validators.tutor import TutorSearchValidator


@pytest.mark.asyncio
async def test_approval_status_all_returns_all_tutors_without_filter():
    filter_instance = await TutorSearchFilter(TutorSearchValidator(approval_status="ALL"))

    assert len(filter_instance._filters) == 0


@pytest.mark.asyncio
async def test_approval_status_pending_adds_status_filter():
    filter_instance = await TutorSearchFilter(
        TutorSearchValidator(approval_status="PENDING")
    )

    assert len(filter_instance._filters) == 1


@pytest.mark.asyncio
async def test_tutor_filter_supports_program_style_and_rating_sort():
    filter_instance = await TutorSearchFilter(
        TutorSearchValidator(
            academic_program="Computer Science",
            teaching_style="Project-based",
            sort="rating:desc",
        )
    )

    assert len(filter_instance._filters) == 2
    assert filter_instance.get_sorting_orders()


@pytest.mark.asyncio
async def test_tutor_rating_sort_uses_mysql_safe_null_ordering():
    filter_instance = await TutorSearchFilter(TutorSearchValidator(sort="rating:desc"))

    order = filter_instance.get_sorting_orders()[0]
    assert "NULLS LAST" not in str(order).upper()
    assert "CASE" in str(order).upper()


@pytest.mark.asyncio
async def test_tutor_id_lookup_keeps_public_only_filter():
    filter_instance = await TutorSearchFilter(
        TutorSearchValidator(
            tutor_id="11111111-1111-4111-8111-111111111111",
            public_only=True,
        )
    )

    combined_filters = " ".join(str(item).lower() for item in filter_instance._filters)
    assert len(filter_instance._filters) == 5
    assert "tutors.id" in combined_filters
    assert "approval_status" in combined_filters
    assert "is_visible" in combined_filters
    assert "tutors.status" in combined_filters
