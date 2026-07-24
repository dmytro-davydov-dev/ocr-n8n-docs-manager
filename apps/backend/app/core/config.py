from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "contract-review-backend"
    app_env: str = "development"
    log_level: str = "INFO"

    api_prefix: str = "/api"
    internal_api_key: str = Field(default="change-me", alias="INTERNAL_API_KEY")

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@postgres:5432/contracts",
        alias="DATABASE_URL",
    )
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/1", alias="CELERY_RESULT_BACKEND")

    documents_storage_path: str = Field(default="/documents", alias="DOCUMENTS_STORAGE_PATH")
    max_upload_size_bytes: int = Field(default=50 * 1024 * 1024, alias="MAX_UPLOAD_SIZE_BYTES")
    allowed_upload_content_types: tuple[str, ...] = ("application/pdf",)

    n8n_webhook_url: str | None = Field(default=None, alias="N8N_WEBHOOK_URL")
    n8n_webhook_timeout_seconds: float = Field(default=5.0, alias="N8N_WEBHOOK_TIMEOUT_SECONDS")


settings = Settings()
