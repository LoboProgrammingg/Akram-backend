"""Akram Backend — Configuration via pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://akram:akram_secret_2026@localhost:5432/akram_db"

    # Security
    SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # Timezone
    TIMEZONE: str = "America/Cuiaba"

    # AI
    AI_PROVIDER: str = "gemini"  # "openai" or "gemini"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Evolution API
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = ""

    # Upload dirs
    UPLOAD_DIR: str = "./data/uploads"
    EXPORT_DIR: str = "./data/exports"

    # Environment
    ENVIRONMENT: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
