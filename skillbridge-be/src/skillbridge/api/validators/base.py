from pydantic import BaseModel, ValidationError

from skillbridge.exceptions import ValidatorError

# Model-level validators (``@model_validator``) report errors against the whole
# model rather than a single field, so pydantic gives them an empty ``loc``.
_MODEL_LEVEL_FIELD = "request"


def _error_field(error: dict) -> str:
    """Name the offending field, falling back for model-level errors.

    ``loc`` is an empty tuple for ``@model_validator`` failures, so indexing it
    directly raises IndexError from inside the exception handler and escapes as
    an unhandled 500.
    """
    location = error.get("loc") or ()
    return str(location[-1]) if location else _MODEL_LEVEL_FIELD


class BaseValidator:
    @staticmethod
    def validate(validator: BaseModel, input_data: BaseModel = None, **extra_fields):
        valid_data = None
        try:
            if input_data is not None:
                if not isinstance(input_data, BaseModel):
                    raise TypeError(
                        f"input_data must be a pydantic model, got "
                        f"{type(input_data).__name__}."
                    )
                valid_data = validator(**input_data.model_dump(), **extra_fields)

            else:
                valid_data = validator(**extra_fields)
            return False, valid_data
        except ValidationError as e:
            messages = []
            for error in e.errors():
                message = error.get("msg", "Invalid value.")
                if message.lower().startswith("value error, "):
                    message = message[len("Value error, "):]
                messages.append(f"{_error_field(error)}: {message}")
            raise ValidatorError(
                message="; ".join(messages) or "Please check the submitted data.",
                status_code=422,
            )
        except Exception as e:
            raise ValidatorError(
                message=str(e) or "Please check the submitted data.",
                status_code=getattr(e, "status_code", 422),
            )
