"""Application configuration using Pydantic Settings v2."""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Runtime
    ENVIRONMENT: str = "development"
    APP_NAME: str = "APAAR-Sutra"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-super-secret-key-32-chars-minimum-in-production"

    # CORS & Security
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    ALLOWED_HOSTS: Union[List[str], str] = ["localhost", "127.0.0.1", "backend", "nginx"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore[return-value]
        raise ValueError(f"Invalid CORS format: {v}")

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore[return-value]
        raise ValueError(f"Invalid ALLOWED_HOSTS format: {v}")

    # PostgreSQL Database
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "apaar_user"
    POSTGRES_PASSWORD: str = "apaar_secure_password_2026"
    POSTGRES_DB: str = "apaar_sutra_db"
    DATABASE_URL: str = (
        "postgresql://apaar_user:apaar_secure_password_2026@postgres:5432/apaar_sutra_db"
    )
    DATABASE_ASYNC_URL: str = (
        "postgresql+asyncpg://apaar_user:apaar_secure_password_2026@postgres:5432/apaar_sutra_db"
    )

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Mock APAAR Gateway
    APAAR_GATEWAY_URL: str = "http://backend:8000/api/v1/mock-apaar"
    APAAR_API_KEY: str = "mock-government-apaar-api-key-test-2026"

    # Observability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
