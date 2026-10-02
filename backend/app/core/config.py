"""Application settings, loaded from environment variables (12-factor style)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "dev-only-insecure-jwt-secret-set-JWT_SECRET-in-production"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Carbon Footprint Navigator API"
    environment: Literal["development", "test", "production"] = "development"

    database_url: str = "postgresql+psycopg://cfn:cfn_dev_password@localhost:5433/cfn"

    jwt_secret: str = INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # Comma-separated list of allowed origins, e.g. "http://localhost:5173,https://app.example.com"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    ai_provider: Literal["anthropic", "demo"] = "demo"
    ai_api_key: str = ""
    ai_model: str = "claude-opus-5-5"
    ai_timeout_seconds: float = 60.0

    seed_emission_factors: bool = True
    seed_demo_data: bool = False
    demo_user_email: str = "demo@carbonnavigator.app"
    demo_user_password: str = Field(default="DemoPass123!", min_length=8)

    rate_limit_auth_per_minute: int = 10
    rate_limit_assistant_per_minute: int = 12

    @field_validator("database_url")
    @classmethod
    def normalise_db_url(cls, value: str) -> str:
        # Render/Heroku style URLs use "postgres://" or "postgresql://" — force the psycopg3 driver.
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://") :]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return self.ai_provider != "demo" and bool(self.ai_api_key)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "production" and (
        settings.jwt_secret == INSECURE_DEFAULT_SECRET or len(settings.jwt_secret) < MIN_SECRET_LENGTH
    ):
        raise RuntimeError(f"JWT_SECRET must be a random value of at least {MIN_SECRET_LENGTH} characters in production.")
    return settings
