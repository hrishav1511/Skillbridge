"""Regression tests for BaseValidator error formatting.

Model-level validators report an empty ``loc``. Indexing that directly raised
IndexError from inside the exception handler, so every ``@model_validator``
failure escaped as an unhandled 500 instead of a usable validation error.
"""

import pytest
from pydantic import BaseModel, Field, model_validator

from skillbridge.api.validators.base import BaseValidator
from skillbridge.api.validators.service import CreateServiceInputValidator
from skillbridge.exceptions import ValidatorError


class _ModelLevelValidator(BaseModel):
    start: int = 1
    end: int = 0

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        return self


class _FieldLevelValidator(BaseModel):
    price: int = Field(ge=0)


def test_model_level_validation_error_is_reported_not_raised_as_indexerror():
    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(validator=_ModelLevelValidator)

    assert exc_info.value.status_code == 422
    assert "end must be later than start" in exc_info.value.message


def test_field_level_validation_error_still_names_the_field():
    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(validator=_FieldLevelValidator, price=-1)

    assert exc_info.value.status_code == 422
    assert exc_info.value.message.startswith("price: ")


def test_service_end_time_before_start_time_reports_a_readable_message():
    """The real-world path: a model-level rule on service creation."""
    from datetime import date, time, timedelta
    from uuid import uuid4

    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(
            validator=CreateServiceInputValidator,
            tutor_id=uuid4(),
            service_name="Python Basics",
            date=date.today() + timedelta(days=1),
            time=time(11, 0),
            end_time=time(10, 0),
            price=30,
            level="BEGINNER",
        )

    assert exc_info.value.status_code == 422
    assert "end_time must be later than time" in exc_info.value.message


def test_past_service_date_reports_a_readable_message():
    from datetime import date, time, timedelta
    from uuid import uuid4

    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(
            validator=CreateServiceInputValidator,
            tutor_id=uuid4(),
            service_name="Python Basics",
            date=date.today() - timedelta(days=1),
            time=time(10, 0),
            end_time=time(11, 0),
            price=30,
            level="BEGINNER",
        )

    assert exc_info.value.status_code == 422
    assert "date cannot be in the past" in exc_info.value.message


def test_non_model_input_data_is_rejected_with_a_clear_message():
    """A plain dict used to surface as \"'dict' object has no attribute 'model_dump'\"."""
    with pytest.raises(ValidatorError) as exc_info:
        BaseValidator.validate(validator=_FieldLevelValidator, input_data={"price": 1})

    assert "must be a pydantic model" in exc_info.value.message
