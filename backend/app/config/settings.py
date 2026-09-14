"""
app/config/settings.py

Centralized configuration management using pydantic-settings.
All settings are read from environment variables / .env file.
This is the single source of truth for all application config.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Usage:
        from app.config.settings import get_settings
        settings = get_settings()
        print(settings.APP_NAME)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "CommerceFlow AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        v = v.strip() if v else ""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use postgresql+asyncpg:// for async support"
            )
        return v

    # ── HuggingFace / Transformers ────────────────────────────────────────────
    HF_HUB_OFFLINE: int = 0
    TRANSFORMERS_OFFLINE: int = 0

    # ── JWT Authentication ────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    # ── LLM Provider (Configurable) ───────────────────────────────────────────
    LLM_PROVIDER: Literal["openrouter", "openai", "anthropic"] = "openrouter"
    LLM_MODEL: str = "qwen/qwen3-30b-a3b:free"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # ── FAISS & Embeddings ────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "faiss/index"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # ── File Uploads ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = "pdf,txt,docx,md"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5174,http://localhost:3000"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FILE: str = "logs/commerceflow.log"
    LOG_MAX_BYTES: int = 10_485_760  # 10 MB
    LOG_BACKUP_COUNT: int = 5

    # ── Computed Properties ───────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS comma-separated string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Parse ALLOWED_EXTENSIONS comma-separated string into a list."""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Returns the cached Settings instance.
    Use this function everywhere — it creates Settings only once.
    """
    return Settings()
