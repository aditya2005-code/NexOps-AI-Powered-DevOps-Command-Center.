from functools import lru_cache
from typing import Literal, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Information
    APP_NAME: str = "NexOps"
    APP_ENV: str = "development"
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Routing & CORS
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = ["http://localhost:5173"]
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Database (Neon PostgreSQL)
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/nexops"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    # JWT Security - to be fully configured in future phases
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # LLM Settings
    LLM_DEFAULT_PROVIDER: Literal["gemini", "groq"] = "gemini"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def sync_environment(cls, v: str, info) -> str:
        # Default to APP_ENV if not explicitly set
        return v or "development"

    @property
    def cors_origins(self) -> list[str]:
        origins = self.BACKEND_CORS_ORIGINS
        if isinstance(origins, list):
            return origins
        if isinstance(origins, str):
            cleaned = origins.strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                import json
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                except Exception:
                    pass
            return [o.strip() for o in cleaned.split(",") if o.strip()]
        return self.ALLOWED_ORIGINS

    @property
    def sqlalchemy_database_url(self) -> str:
        """Ensure psycopg3 driver prefix for PostgreSQL URLs."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
