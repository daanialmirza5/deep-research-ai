"""Typed application configuration. Every field mirrors a variable documented
in .env.example; a value present in the real environment always wins over the
repo-root .env file (pydantic-settings precedence), so Docker Compose's
`env_file:` injection and local `.env` files both work unmodified.

Defaults below are safe, non-secret development fallbacks only — production
deployments must override SECRET_KEY, POSTGRES_PASSWORD-derived DATABASE_URL,
and every *_API_KEY via real environment variables.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    environment: str = "development"
    log_level: str = "INFO"
    backend_cors_origins: str = "http://localhost:3000"

    # --- Security / JWT ---
    secret_key: str = "change-me-to-a-long-random-value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- OAuth ---
    google_client_id: str = ""
    google_client_secret: str = ""
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8000"

    # --- Postgres ---
    database_url: str = (
        "postgresql+asyncpg://dra_user:change-me@localhost:5432/deep_research_ai"
    )

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- MinIO ---
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "dra_minio"
    minio_root_password: str = "change-me-8chars-min"
    minio_use_ssl: bool = False
    minio_bucket_documents: str = "dra-documents"
    minio_bucket_reports: str = "dra-reports"

    # --- AI providers (see ai/llm/, selected via ai_provider) ---
    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Embeddings (see ai/embeddings/, selected via embedding_provider) ---
    embedding_provider: str = "bge"
    embedding_dimension: int = 1024
    bge_model_name: str = "BAAI/bge-large-en-v1.5"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Search tools (ai/tools/) ---
    google_search_api_key: str = ""
    google_search_engine_id: str = ""
    semantic_scholar_api_key: str = ""
    github_token: str = ""

    # --- Agent pipeline ---
    max_revision_loops: int = 2
    agent_timeout_seconds: int = 120

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
