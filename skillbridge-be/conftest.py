"""Shared pytest fixtures for root-level and package tests."""

from uuid import uuid4
from typing import Any, Dict

import pytest


@pytest.fixture
def tokens() -> Dict[str, Any]:
    """Create access and refresh tokens for authentication unit tests."""
    from skillbridge.api.repositories.auth.token import TokenRepository

    return TokenRepository.create_tokens(str(uuid4()))
