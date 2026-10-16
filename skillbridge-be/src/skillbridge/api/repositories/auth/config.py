import os
import secrets

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_EPHEMERAL_DEVELOPMENT_SECRET = secrets.token_urlsafe(48)


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # JWT Settings
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY",
            os.getenv("SECRET_KEY", _EPHEMERAL_DEVELOPMENT_SECRET),
        )
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_AUDIENCE: str | None = None
    JWT_ISSUER: str | None = None
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY",
            os.getenv("JWT_SECRET_KEY", _EPHEMERAL_DEVELOPMENT_SECRET),
        )
    )

    # Security
    BCRYPT_ROUNDS: int = 12
    PASSWORD_MIN_LENGTH: int = 8

    # Cookie Settings
    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"

    @model_validator(mode="after")
    def require_production_secrets(self):
        if os.getenv("ENV", "development").lower() == "deployment":
            if not os.getenv("JWT_SECRET_KEY") and not os.getenv("SECRET_KEY"):
                raise ValueError("JWT_SECRET_KEY or SECRET_KEY must be configured in deployment")
        return self


auth_config = AuthConfig()
