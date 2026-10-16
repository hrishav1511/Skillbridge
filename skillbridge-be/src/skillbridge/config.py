import os
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DOTENV = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=DOTENV, extra="ignore")

    # FastAPI
    ENV: str
    API_STR: str = "/v1"
    PROJECT_NAME: str = "SkillBridge Application Backend"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    DOMAIN: str

    # MySQL-specific settings
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOSTNAME: str = "localhost"
    MYSQL_PORT: int = 3306  # Default MySQL port
    MYSQL_DATABASE: str
    MYSQL_ROOT_PASSWORD: str

    # Optional: MySQL-specific performance settings
    MYSQL_POOL_SIZE: int = 20
    MYSQL_MAX_OVERFLOW: int = 10

    # SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    SQLALCHEMY_DATABASE_URI: str | None = None

    DEBUG: bool
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    STORAGE_DRIVER: str
    SERVICE_TIMEZONE: str = "Europe/Berlin"

    # OpenAI moderation
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODERATION_ENABLED: bool = False
    OPENAI_MODERATION_MODEL: str = "omni-moderation-latest"
    OPENAI_MODERATION_TIMEOUT_SECONDS: float = 10.0
    OPENAI_MODERATION_MAX_RETRIES: int = 2

    # AWS / S3
    AWS_REGION: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
    AWS_S3_BUCKET_NAME: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    S3_TUTOR_MEDIA_PREFIX: str = "tutor-media"

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v, info):
        if isinstance(v, str):
            return v

        values = info.data

        return (
            f"mysql+asyncmy://"
            f"{values.get('MYSQL_USER')}:"
            f"{values.get('MYSQL_PASSWORD')}@"
            f"{values.get('MYSQL_HOSTNAME')}:"
            f"{values.get('MYSQL_PORT')}/"
            f"{values.get('MYSQL_DATABASE')}"
        )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return v


settings = Settings()
