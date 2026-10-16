"""Authorization and lookup failures must not surface as 500s.

The repositories raised bare Exception/PermissionError/LookupError, which carry
no status_code. handle_exceptions defaults those to 500 and then replaces the
message with "Something went wrong while processing the request." - so a caller
was denied with no usable reason, and a genuine server fault was
indistinguishable from a permission problem.
"""

import inspect

import pytest

from skillbridge.api.repositories import favorite as favorite_repository
from skillbridge.api.repositories import service as service_repository
from skillbridge.api.repositories import tutor as tutor_repository
from skillbridge.exceptions import (
    BaseExceptionMixin,
    NotFoundError,
    UnAuthorizedError,
    handle_exceptions,
)

REPOSITORY_MODULES = [
    favorite_repository,
    service_repository,
    tutor_repository,
]


@pytest.mark.parametrize(
    "module", REPOSITORY_MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1]
)
def test_repositories_raise_no_untyped_exceptions(module):
    """Every raise in these repositories must carry an HTTP status."""
    source = inspect.getsource(module)
    for bare in ('raise Exception(', 'raise PermissionError(', 'raise LookupError('):
        assert bare not in source, (
            f"{module.__name__} still raises {bare!r}, which handle_exceptions "
            f"turns into a sanitised 500"
        )


@pytest.mark.parametrize(
    "exception,expected_status",
    [
        (UnAuthorizedError(message="Admin access required.", status_code=403), 403),
        (NotFoundError(message="Revision not found.", status_code=404), 404),
        (BaseExceptionMixin("Revision is already ACCEPTED.", status_code=409), 409),
    ],
)
@pytest.mark.asyncio
async def test_typed_exceptions_keep_their_status_and_message(exception, expected_status):
    @handle_exceptions
    async def endpoint():
        raise exception

    response = await endpoint()
    assert response.status_code == expected_status
    # Below 500 the message is preserved rather than replaced with a generic one.
    assert exception.message.encode() in response.body


@pytest.mark.asyncio
async def test_untyped_exceptions_are_still_sanitised_as_500():
    """Genuine faults must stay generic - this is the behaviour worth keeping."""

    @handle_exceptions
    async def endpoint():
        raise RuntimeError("connection pool exhausted at 10.0.0.4:3306")

    response = await endpoint()
    assert response.status_code == 500
    assert b"10.0.0.4" not in response.body
    assert b"Something went wrong" in response.body
