from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Loris PMO"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
    secret_key: str = Field(min_length=32)
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    frontend_url: str = "http://localhost:5173"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    ai_provider: Literal["gemini"] = "gemini"
    ai_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    ai_max_output_tokens: int = Field(default=4096, ge=128, le=8192)
    ai_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    document_storage_path: str = ".data/documents"
    document_max_upload_mb: int = Field(default=10, ge=1, le=100)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
