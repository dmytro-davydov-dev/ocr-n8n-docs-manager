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

    # Blockers #4 ("no automated recovery for stuck/failed documents"): cap on
    # how many times the watchdog (n8n `02-processing-watchdog`) may
    # auto-retry a `failed` document via POST .../auto-retry before it must
    # stop and only surface the document for a human, same as before.
    document_auto_retry_max: int = Field(default=3, alias="DOCUMENT_AUTO_RETRY_MAX")
    # Mirrors the STALE_THRESHOLD_MS the watchdog workflow
    # (n8n/workflows/02-processing-watchdog.json) uses to flag a document
    # stuck in `queued`/`processing` for a human. /reprocess uses the same
    # threshold to gate its `queued`/`processing` -> `queued` override, so an
    # operator can only force-reset a document once it's old enough to
    # actually be wedged rather than genuinely mid-pipeline.
    document_stuck_threshold_minutes: int = Field(default=15, alias="DOCUMENT_STUCK_THRESHOLD_MINUTES")

    # WS-03: OCR engine is swappable via config only (ADR-010, WS-03 Done Criteria).
    # "paddleocr" is the ADR-010 default; "null" is a no-op engine for environments
    # without the (heavy) paddleocr/paddlepaddle dependencies installed.
    ocr_engine: str = Field(default="paddleocr", alias="OCR_ENGINE")
    ocr_rasterize_dpi: int = Field(default=200, alias="OCR_RASTERIZE_DPI")
    ocr_max_retries: int = Field(default=3, alias="OCR_MAX_RETRIES")

    # ADR-008 named "tasks remain stuck" as a risk to mitigate with time
    # limits; none were previously configured, so a hang inside a task (e.g.
    # an OCR engine call that never returns and never raises) never produced
    # an exception for the task to handle -- the document just stayed
    # 'processing' forever with no automated way out. `soft_*` raises
    # `SoftTimeLimitExceeded` inside the task so it gets a chance to persist
    # a terminal failure state before the hard limit kills the worker child.
    validate_file_soft_time_limit_seconds: int = Field(
        default=30, alias="VALIDATE_FILE_SOFT_TIME_LIMIT_SECONDS"
    )
    validate_file_time_limit_seconds: int = Field(default=45, alias="VALIDATE_FILE_TIME_LIMIT_SECONDS")
    ocr_soft_time_limit_seconds: int = Field(default=300, alias="OCR_SOFT_TIME_LIMIT_SECONDS")
    ocr_time_limit_seconds: int = Field(default=330, alias="OCR_TIME_LIMIT_SECONDS")

    # WS-03 Phase 3: LLM provider is a single OpenAI-compatible HTTP client
    # (ADR-012 — Ollama/vLLM/Azure OpenAI all speak this API), so switching
    # providers is a config change (base URL/model/key), never a code change.
    llm_provider: str = Field(default="openai_compatible", alias="LLM_PROVIDER")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")
    extract_fields_soft_time_limit_seconds: int = Field(
        default=90, alias="EXTRACT_FIELDS_SOFT_TIME_LIMIT_SECONDS"
    )
    extract_fields_time_limit_seconds: int = Field(default=120, alias="EXTRACT_FIELDS_TIME_LIMIT_SECONDS")

    # WS-03 Phase 5: embedding provider follows the same OpenAI-compatible
    # pattern as the LLM provider (ADR-017).
    embedding_provider: str = Field(default="openai_compatible", alias="EMBEDDING_PROVIDER")
    embedding_base_url: str | None = Field(default=None, alias="EMBEDDING_BASE_URL")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_timeout_seconds: float = Field(default=30.0, alias="EMBEDDING_TIMEOUT_SECONDS")
    embedding_max_retries: int = Field(default=3, alias="EMBEDDING_MAX_RETRIES")
    generate_embeddings_soft_time_limit_seconds: int = Field(
        default=180, alias="GENERATE_EMBEDDINGS_SOFT_TIME_LIMIT_SECONDS"
    )
    generate_embeddings_time_limit_seconds: int = Field(
        default=210, alias="GENERATE_EMBEDDINGS_TIME_LIMIT_SECONDS"
    )
    # ADR-016: native pgvector column dimension. Must match whatever
    # `embedding_model` actually produces (1536 for text-embedding-3-small,
    # the default) -- pgvector enforces this at the database level, so a
    # provider/model change that alters the output dimension requires a
    # matching migration, not just an env var change.
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")

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
