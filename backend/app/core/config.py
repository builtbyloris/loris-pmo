from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_https_origin(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and "*" not in parsed.netloc
        and parsed.path in {"", "/"}
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


class Settings(BaseSettings):
    app_name: str = "Loris PMO"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
    secret_key: str = Field(min_length=32)
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    frontend_url: str = "http://localhost:5173"
    cors_allowed_origins: str = ""
    trusted_hosts: str = "localhost,127.0.0.1,testserver,test"
    cookie_domain: str | None = None
    cookie_same_site: Literal["lax", "strict", "none"] = "lax"
    api_docs_enabled: bool = False
    debug: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    database_ssl_mode: Literal["disable", "prefer", "require", "verify-ca", "verify-full"] = (
        "disable"
    )
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    ai_provider: Literal["gemini"] = "gemini"
    ai_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    ai_max_output_tokens: int = Field(default=4096, ge=128, le=8192)
    ai_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    embedding_batch_size: int = Field(default=20, ge=1, le=100)
    embedding_version: str = Field(default="v1", min_length=1, max_length=32)
    knowledge_candidate_limit: int = Field(default=500, ge=50, le=2000)
    document_storage_backend: Literal["local", "s3"] = "local"
    document_storage_path: str = ".data/documents"
    document_max_upload_mb: int = Field(default=10, ge=1, le=100)
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_request_timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)
    integration_token_encryption_key: str | None = None
    integration_timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/integrations/oauth/google/callback"
    )
    google_oauth_scopes: str = (
        "openid email https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/gmail.readonly"
    )
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    github_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/integrations/oauth/github/callback"
    )
    github_oauth_scopes: str = "read:user"
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

    @property
    def allowed_origins(self) -> list[str]:
        return _csv(self.cors_allowed_origins) or [self.frontend_url.rstrip("/")]

    @property
    def allowed_hosts(self) -> list[str]:
        return _csv(self.trusted_hosts)

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.app_env != "production":
            return self
        errors: list[str] = []
        lowered_secret = self.secret_key.lower()
        if len(self.secret_key) < 48 or any(
            marker in lowered_secret
            for marker in ("replace", "change-me", "example", "secret", "generate")
        ):
            errors.append("SECRET_KEY must be a strong production value of at least 48 characters")
        database = urlparse(self.database_url)
        if not self.database_url.startswith("postgresql+asyncpg://"):
            errors.append("DATABASE_URL must use PostgreSQL with the asyncpg driver")
        if not database.hostname or not database.username or not database.password:
            errors.append("DATABASE_URL must include a host and non-empty credentials")
        if database.password and any(
            marker in database.password.lower() for marker in ("password", "replace", "example")
        ):
            errors.append("DATABASE_URL contains a placeholder password")
        if self.database_ssl_mode not in {"require", "verify-ca", "verify-full"}:
            errors.append("DATABASE_SSL_MODE must require or verify TLS")
        if not _is_https_origin(self.frontend_url):
            errors.append("FRONTEND_URL must be an HTTPS origin")
        if not self.allowed_origins or any(
            not _is_https_origin(origin) for origin in self.allowed_origins
        ):
            errors.append("CORS_ALLOWED_ORIGINS must contain only explicit HTTPS origins")
        if (
            not self.allowed_hosts
            or any("*" in host or "://" in host or "/" in host for host in self.allowed_hosts)
        ):
            errors.append("TRUSTED_HOSTS must contain explicit host names")
        if self.debug or self.api_docs_enabled:
            errors.append("DEBUG and API_DOCS_ENABLED must be disabled")
        integrations_enabled = any(
            (
                self.google_oauth_client_id,
                self.google_oauth_client_secret,
                self.github_oauth_client_id,
                self.github_oauth_client_secret,
            )
        )
        if integrations_enabled and not self.integration_token_encryption_key:
            errors.append("INTEGRATION_TOKEN_ENCRYPTION_KEY is required when OAuth is enabled")
        if self.integration_token_encryption_key:
            try:
                Fernet(self.integration_token_encryption_key.encode())
            except (TypeError, ValueError):
                errors.append("INTEGRATION_TOKEN_ENCRYPTION_KEY must be a valid Fernet key")
        for name, client_id, client_secret, redirect in (
            (
                "Google",
                self.google_oauth_client_id,
                self.google_oauth_client_secret,
                self.google_oauth_redirect_uri,
            ),
            (
                "GitHub",
                self.github_oauth_client_id,
                self.github_oauth_client_secret,
                self.github_oauth_redirect_uri,
            ),
        ):
            if bool(client_id) != bool(client_secret):
                errors.append(f"{name} OAuth client ID and secret must be configured together")
            if (client_id or client_secret) and urlparse(redirect).scheme != "https":
                errors.append(f"{name} OAuth redirect URI must use HTTPS")
        if self.document_storage_backend == "local":
            if not Path(self.document_storage_path).expanduser().is_absolute():
                errors.append("DOCUMENT_STORAGE_PATH must be absolute in production")
        elif not self.s3_bucket or not self.s3_region:
            errors.append("S3_BUCKET and S3_REGION are required for S3 storage")
        if self.s3_endpoint_url and urlparse(self.s3_endpoint_url).scheme != "https":
            errors.append("S3_ENDPOINT_URL must use HTTPS in production")
        if bool(self.s3_access_key_id) != bool(self.s3_secret_access_key):
            errors.append("S3 access key ID and secret must be configured together")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
