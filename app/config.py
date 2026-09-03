from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Madad — Medical Crowdfunding"
    environment: str = "development"
    database_url: str = "sqlite:///./madad.db"

    jwt_secret: str = "dev-only-change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24  # 24h

    cors_origins: str = "*"

    admin_seed_email: str = "admin@madad.pk"
    admin_seed_password: str = "admin12345"


@lru_cache
def get_settings() -> Settings:
    return Settings()
