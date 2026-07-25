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

    # WS-03: OCR engine is swappable via config only (ADR-010, WS-03 Done Criteria).
    # "paddleocr" is the ADR-010 default; "null" is a no-op engine for environments
    # without the (heavy) paddleocr/paddlepaddle dependencies installed.
    ocr_engine: str = Field(default="paddleocr", alias="OCR_ENGINE")
    ocr_rasterize_dpi: int = Field(default=200, alias="OCR_RASTERIZE_DPI")
    ocr_max_retries: int = Field(default=3, alias="OCR_MAX_RETRIES")

    # WS-03 Phase 3: LLM provider is a single OpenAI-compatible HTTP client
    # (ADR-012 — Ollama/vLLM/Azure OpenAI all speak this API), so switching
    # providers is a config change (base URL/model/key), never a code change.
    llm_provider: str = Field(default="openai_compatible", alias="LLM_PROVIDER")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")

    # WS-03 Phase 5: embedding provider follows the same OpenAI-compatible
    # pattern as the LLM provider (ADR-017).
    embedding_provider: str = Field(default="openai_compatible", alias="EMBEDDING_PROVIDER")
    embedding_base_url: str | None = Field(default=None, alias="EMBEDDING_BASE_URL")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_timeout_seconds: float = Field(default=30.0, alias="EMBEDDING_TIMEOUT_SECONDS")
    embedding_max_retries: int = Field(default=3, alias="EMBEDDING_MAX_RETRIES")

    # ADR-018: configurable chunk token limit/overlap. Token count is
    # approximated by whitespace splitting to avoid pulling in a
    # model-specific tokenizer dependency for the MVP.
    chunk_token_limit: int = Field(default=500, alias="CHUNK_TOKEN_LIMIT")
    chunk_overlap_tokens: int = Field(default=50, alias="CHUNK_OVERLAP_TOKENS")

    # Phase 5 (ADR-019): hybrid retrieval ranking weights. Must not both be
    # zero; kept as separate knobs (rather than a single mix ratio) so an
    # operator can disable one signal entirely (e.g. vector-only) via env.
    search_keyword_weight: float = Field(default=0.4, alias="SEARCH_KEYWORD_WEIGHT")
    search_vector_weight: float = Field(default=0.6, alias="SEARCH_VECTOR_WEIGHT")
    search_default_limit: int = Field(default=10, alias="SEARCH_DEFAULT_LIMIT")
    chat_context_chunks: int = Field(default=5, alias="CHAT_CONTEXT_CHUNKS")


settings = Settings()
