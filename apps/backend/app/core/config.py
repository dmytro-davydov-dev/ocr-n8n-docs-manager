from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "contract-review-backend"
    app_env: str = "development"
    log_level: str = "INFO"

    api_prefix: str = "/api"
    internal_api_key: str = Field(default="change-me", alias="INTERNAL_API_KEY")

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@postgres:5432/contracts",
        alias="DATABASE_URL",
    )
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/1", alias="CELERY_RESULT_BACKEND")


settings = Settings()
