from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

# Your imports
from skillbridge.config import settings
from skillbridge.database.models.sqlalchemy.base import Base
from skillbridge.database.models.sqlalchemy.base import UUIDType

# Import all your models here so Alembic can see them
from skillbridge.database.models.sqlalchemy import *  # noqa: F403, F401

# this is the Alembic Config object
config = context.config

# Build the sync database URL directly (no async at all for Alembic)
if not config.get_main_option("sqlalchemy.url"):
    if settings.ENV == "local":
        # IMPORTANT: Use pymysql, NOT asyncmy
        sync_database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@localhost:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"

    elif settings.ENV == "deployment":
        sync_database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@skillbridge-mysql:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    else:
        sync_database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@skillbridge-mysql:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"

    config.set_main_option("sqlalchemy.url", sync_database_url)


# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    if type_ == "type" and isinstance(obj, UUIDType):
        autogen_context.imports.add("import sqlalchemy as sa")
        return "sa.CHAR(36)"
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # Get the sync URL directly from config
    url = config.get_main_option("sqlalchemy.url")

    # Create a sync engine with pymysql
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,  # Use the custom render_item function
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
