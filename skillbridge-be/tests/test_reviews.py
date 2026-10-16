import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skillbridge.api.filters.review import ServiceReviewSearchFilter, TutorReviewSearchFilter
from skillbridge.api.repositories.review import format_average_rating
from skillbridge.api.schemas.review import (
    CreateServiceReviewInput,
    CreateTutorReviewInput,
    ServiceReviewQueryCriteria,
    TutorReviewQueryCriteria,
)


def test_tutor_review_input_accepts_rating_in_range():
    payload = CreateTutorReviewInput(
        tutor_id=uuid4(),
        student_id=uuid4(),
        rating=8.5,
        comment="Very helpful tutor",
    )

    assert payload.rating == 8.5


def test_service_review_input_accepts_rating_in_range():
    payload = CreateServiceReviewInput(
        service_id=uuid4(),
        student_id=uuid4(),
        rating=9.0,
        comment="Excellent session",
    )

    assert payload.rating == 9.0


def test_format_average_rating_handles_missing_reviews():
    assert format_average_rating(None) == "No Review Yet"
    assert format_average_rating(8.5) == "8.5/10"


def test_review_rating_must_stay_within_ten():
    with pytest.raises(ValidationError):
        CreateTutorReviewInput(
            tutor_id=uuid4(),
            student_id=uuid4(),
            rating=11,
            comment="Too high",
        )


def test_tutor_review_filter_uses_query_criteria():
    async def build_query():
        search_filter = await TutorReviewSearchFilter(
            TutorReviewQueryCriteria(tutor_id=uuid4(), student_id=uuid4())
        )
        return await search_filter.get_query()

    query = asyncio.run(build_query())
    assert "tutor_reviews" in str(query)
    assert "student_id" in str(query)


def test_service_review_filter_uses_query_criteria():
    async def build_query():
        search_filter = await ServiceReviewSearchFilter(
            ServiceReviewQueryCriteria(service_id=uuid4(), student_id=uuid4())
        )
        return await search_filter.get_query()

    query = asyncio.run(build_query())
    assert "service_reviews" in str(query)
    assert "student_id" in str(query)
