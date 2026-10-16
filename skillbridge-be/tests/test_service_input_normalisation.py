"""Regression tests for service create/update form input handling.

The endpoints used to build an intermediate CreateServiceInput/UpdateServiceInput
model *outside* the guarded validation path, so any coercion failure there (a
level in the wrong case, for example) escaped as an unhandled 500 instead of a
422 the tutor could act on.
"""

from datetime import date, time, timedelta
from uuid import uuid4

import pytest

from skillbridge.api.api_v1.endpoints.service import _normalise_level
from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.service import (
    CreateServiceInputValidator,
    UpdateServiceInputValidator,
)
from skillbridge.exceptions import ValidatorError


@pytest.mark.parametrize(
    "supplied,expected",
    [
        ("BEGINNER", "BEGINNER"),
        ("beginner", "BEGINNER"),
        ("  Intermediate  ", "INTERMEDIATE"),
        ("advanced", "ADVANCED"),
    ],
)
def test_level_is_accepted_in_any_case(supplied, expected):
    assert _normalise_level(supplied) == expected


def test_empty_level_becomes_none_so_it_reads_as_missing():
    assert _normalise_level("") is None
    assert _normalise_level("   ") is None


def test_non_string_level_is_passed_through_untouched():
    assert _normalise_level(None) is None


def _create_kwargs(**overrides):
    payload = {
        "tutor_id": uuid4(),
        "service_name": "Python Basics",
        "date": date.today() + timedelta(days=3),
        "time": time(10, 0),
        "end_time": time(11, 0),
        "price": 30,
        "level": "BEGINNER",
    }
    payload.update(overrides)
    return payload


def test_lowercase_level_validates_once_normalised():
    has_error, valid = BaseValidator.validate(
        validator=CreateServiceInputValidator,
        **_create_kwargs(level=_normalise_level("beginner")),
    )
    assert has_error is False
    assert str(valid.level) == "BEGINNER"


def test_unknown_level_is_a_422_not_a_500():
    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(
            validator=CreateServiceInputValidator,
            **_create_kwargs(level=_normalise_level("wizard")),
        )
    assert exc_info.value.status_code == 422
    assert "level" in exc_info.value.message


def test_missing_level_is_a_422_naming_the_field():
    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(
            validator=CreateServiceInputValidator,
            **_create_kwargs(level=_normalise_level("")),
        )
    assert exc_info.value.status_code == 422
    assert "level" in exc_info.value.message


def test_update_accepts_a_lowercase_level_and_omitted_fields():
    has_error, valid = BaseValidator.validate(
        validator=UpdateServiceInputValidator,
        service_name="Renamed",
        level=_normalise_level("advanced"),
    )
    assert has_error is False
    assert str(valid.level) == "ADVANCED"
    assert valid.price is None
