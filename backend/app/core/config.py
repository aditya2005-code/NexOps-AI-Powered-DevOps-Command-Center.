from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional, Union
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
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

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
    LLM_PROVIDER: Optional[str] = None
    LLM_DEFAULT_PROVIDER: Literal["gemini", "groq"] = "gemini"
    LLM_MODEL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: Optional[int] = 2048
    GOOGLE_API_KEY: str = ""
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Switch Integration (Agent Bridge)
    SWITCH_ENABLED: bool = False
    SWITCH_CORE_URL: Union[str, None] = None
    SWITCH_API_KEY: Union[str, None] = None
    SWITCH_AGENT_ID: Union[str, None] = None
    SWITCH_RECONNECT_INITIAL_DELAY: float = 2.0
    SWITCH_RECONNECT_MAX_DELAY: float = 60.0
    SWITCH_CONNECTION_TIMEOUT: float = 15.0
    SWITCH_ROOM_PROJECT_MAPPING: Union[str, dict[str, str]] = Field(default_factory=dict)

    # Project Workspaces for Safe Source-Code Investigation
    PROJECT_WORKSPACES_ROOT: Optional[str] = None
    PROJECT_WORKSPACE_MAPPING: Union[str, dict[str, str]] = Field(default_factory=dict)

    # Phase 5.4: Controlled Patch Application & Approval Settings
    DEV_APPROVAL_ENABLED: bool = True
    DEV_APPROVAL_ACTOR: str = "dev_reviewer_unverified"
    NEXOPS_WORKTREE_DIR: Optional[str] = None
    GIT_EXECUTABLE_PATH: Optional[str] = None
    GIT_SUBPROCESS_TIMEOUT: float = 30.0

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def sync_environment(cls, v: str, info) -> str:
        # Default to APP_ENV if not explicitly set
        return v or "development"

    @property
    def effective_llm_provider(self) -> str:
        return (self.LLM_PROVIDER or self.LLM_DEFAULT_PROVIDER or "gemini").lower().strip()

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        key = self.GEMINI_API_KEY or self.GOOGLE_API_KEY
        return key.strip() if key and key.strip() else None

    @property
    def effective_groq_api_key(self) -> Optional[str]:
        key = self.GROQ_API_KEY
        return key.strip() if key and key.strip() else None

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

    @property
    def switch_ws_url(self) -> Union[str, None]:
        """Convert SWITCH_CORE_URL to WebSocket URL for Agent Bridge connection."""
        if not self.SWITCH_CORE_URL:
            return None
        url = self.SWITCH_CORE_URL.rstrip("/")
        if url.startswith("https://"):
            ws_base = "wss://" + url[len("https://"):]
        elif url.startswith("http://"):
            ws_base = "ws://" + url[len("http://"):]
        elif url.startswith("wss://") or url.startswith("ws://"):
            ws_base = url
        else:
            ws_base = f"ws://{url}"
        return f"{ws_base}/gateway/changes/ws"

    @property
    def switch_ops_url(self) -> Union[str, None]:
        """Base URL for Switch HTTP operations."""
        if not self.SWITCH_CORE_URL:
            return None
        return f"{self.SWITCH_CORE_URL.rstrip('/')}/ops"

    @property
    def room_project_mapping(self) -> dict[str, str]:
        """Map of Switch room IDs to Project names or UUIDs."""
        mapping = self.SWITCH_ROOM_PROJECT_MAPPING
        if isinstance(mapping, dict):
            return mapping
        if isinstance(mapping, str):
            cleaned = mapping.strip()
            if not cleaned:
                return {}
            if cleaned.startswith("{") and cleaned.endswith("}"):
                import json
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict):
                        return {str(k): str(v) for k, v in parsed.items()}
                except Exception:
                    pass
            # Parse comma-separated "room_id:project_name,room_2:project_2"
            result: dict[str, str] = {}
            for item in cleaned.split(","):
                if ":" in item:
                    k, v = item.split(":", 1)
                    if k.strip() and v.strip():
                        result[k.strip()] = v.strip()
            return result
        return {}

    @property
    def project_workspace_mapping(self) -> dict[str, str]:
        """Map of project IDs or names to absolute workspace paths on disk."""
        mapping = self.PROJECT_WORKSPACE_MAPPING
        if isinstance(mapping, dict):
            return mapping
        if isinstance(mapping, str):
            cleaned = mapping.strip()
            if not cleaned:
                return {}
            if cleaned.startswith("{") and cleaned.endswith("}"):
                import json
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict):
                        return {str(k): str(v) for k, v in parsed.items()}
                except Exception:
                    pass
            result: dict[str, str] = {}
            for pair in cleaned.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    if k.strip() and v.strip():
                        result[k.strip()] = v.strip()
                elif ":" in pair:
                    k, v = pair.split(":", 1)
                    if k.strip() and v.strip():
                        result[k.strip()] = v.strip()
            return result
        return {}

    def get_project_workspace_path(self, project_id_or_name: Optional[str]) -> Optional[Path]:
        """Safely resolve configured workspace path for a project, if defined."""
        if not project_id_or_name:
            return None
        target = self.project_workspace_mapping.get(str(project_id_or_name))
        if target:
            p = Path(target)
            if p.is_dir():
                return p.resolve()
        if self.PROJECT_WORKSPACES_ROOT:
            candidate = Path(self.PROJECT_WORKSPACES_ROOT) / str(project_id_or_name)
            if candidate.is_dir():
                return candidate.resolve()
        return None



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
