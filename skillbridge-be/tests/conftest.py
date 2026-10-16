"""
Global pytest configuration and fixtures for SkillBridge tests.
"""

pytest_plugins = ["pytest_asyncio"]

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from skillbridge.database.models.sqlalchemy.base import Base
from skillbridge.database.db.database import get_session
from skillbridge.utils.renderer import Status


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create async SQLAlchemy engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Create a new database session for a test."""
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            await session.begin_nested()
            yield session
            await session.close()
        await trans.rollback()


@pytest.fixture
def tutor_user_payload() -> Dict[str, Any]:
    """Create a test tutor user JWT payload."""
    tutor_id = uuid4()
    user_id = uuid4()
    return {
        "sub": str(user_id),
        "email": "tutor@example.com",
        "role": "tutor",
        "role_id": uuid4(),
        "tutor_id": tutor_id,
        "student_id": None,
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture
def admin_user_payload() -> Dict[str, Any]:
    """Create a test admin user JWT payload."""
    user_id = uuid4()
    return {
        "sub": str(user_id),
        "email": "admin@example.com",
        "role": "admin",
        "role_id": uuid4(),
        "tutor_id": None,
        "student_id": None,
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture
def student_user_payload() -> Dict[str, Any]:
    """Create a test student user JWT payload."""
    student_id = uuid4()
    user_id = uuid4()
    return {
        "sub": str(user_id),
        "email": "student@example.com",
        "role": "student",
        "role_id": uuid4(),
        "tutor_id": None,
        "student_id": student_id,
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture
def test_service_input() -> Dict[str, Any]:
    """Create a test service input."""
    from datetime import date, time
    return {
        "tutor_id": uuid4(),
        "service_name": "Test Python Tutoring",
        "description": "Learn Python basics",
        "date": date.today(),
        "time": time(14, 30),
        "price": 50,
        "level": "BEGINNER",
        "joining_link": "https://zoom.us/test",
    }


@pytest_asyncio.fixture
async def session_factory(test_engine, monkeypatch):
    """Point every ``get_session`` in the app at the in-memory test database.

    The application imports ``get_session`` by value into each module, so the
    rebind has to happen on every module that holds a reference rather than on
    the definition site alone.
    """
    import types
    from contextlib import asynccontextmanager

    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    @asynccontextmanager
    async def patched_get_session():
        async with factory() as session:
            yield session

    for name, module in list(sys.modules.items()):
        if (
            name.startswith("skillbridge")
            and isinstance(module, types.ModuleType)
            and getattr(module, "get_session", None) is not None
        ):
            monkeypatch.setattr(module, "get_session", patched_get_session, raising=False)

    return factory


@pytest_asyncio.fixture
async def api_client(session_factory):
    """An httpx client bound to the real FastAPI app over the test database."""
    from httpx import ASGITransport, AsyncClient

    from skillbridge.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def auth_header(user_id) -> Dict[str, str]:
    """Build an Authorization header holding a real access token."""
    from skillbridge.api.repositories.auth.token import TokenRepository

    token = TokenRepository.create_tokens(str(user_id))["access_token"]
    return {"Authorization": f"Bearer {token}"}
