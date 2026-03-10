from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Task Management API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./tasks.db"

    RATE_LIMIT_DEFAULT: str = "60/minute"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
