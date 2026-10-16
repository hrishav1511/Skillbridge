from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from skillbridge.config import settings

# Changed: Use asyncmy instead of asyncpg, and adjust the URL format
SQLALCHEMY_DATABASE_URL = (
    # For deployment (container environment)
    f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@skillbridge-mysql:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    if settings.ENV == "deployment"
    # For local development
    else f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOSTNAME}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=False,
    pool_recycle=3600,
)

async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


class TimestampMixin:
    @classmethod
    async def latest(cls, session: AsyncSession = None):
        result = await session.execute(select(cls).order_by(cls.created_at.desc()))
        return result.scalars().first()
