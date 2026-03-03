"""Application settings model and config helpers.

Settings are read from environment variables so local `.env`, shell values,
and CI values can be layered in a predictable order.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Strongly typed runtime settings for local development and CI."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    gcp_project_id: str = Field(default="gen-lang-client-0545732168")
    gcp_region: str = Field(default="us-central1")
    gemini_model: str = Field(default="gemini-embedding-001")
    gemini_generation_model: str = Field(default="gemini-2.5-flash")
    embedding_provider: str = Field(default="vertex_gemini")
    gemini_api_key: str | None = Field(default=None)

    ikea_raw_csv_path: str = Field(default="data/IKEA_product_catalog.csv")
    duckdb_path: str = Field(default="data/ikea.duckdb")
    default_query_limit: int = Field(default=25, ge=1, le=200)
    default_market: str = Field(default="Germany")
    embedding_parallelism: int = Field(default=8, ge=1, le=64)
    embedding_batch_size: int = Field(default=16, ge=1, le=256)
    embedding_dimensions: int = Field(default=256, ge=64, le=3072)
    embedding_requests_per_minute: int = Field(default=90, ge=1, le=10_000)
    embedding_max_retries: int = Field(default=5, ge=0, le=20)
    embedding_retry_base_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    embedding_retry_max_seconds: float = Field(default=90.0, ge=1.0, le=600.0)
    embedding_retry_jitter_seconds: float = Field(default=1.0, ge=0.0, le=10.0)
    embedding_upsert_chunk_size: int = Field(default=25, ge=1, le=1000)
    eval_generation_batch_size: int = Field(default=25, ge=1, le=200)
    eval_generation_parallelism: int = Field(default=4, ge=1, le=32)
    eval_generation_max_rounds: int = Field(default=8, ge=1, le=50)
    vss_build_index: bool = Field(default=False)
    vss_metric: str = Field(default="cosine")
    retrieval_low_confidence_threshold: float = Field(default=0.15)
    django_secret_key: str = Field(default="dev-only-secret")
    django_debug: bool = Field(default=True)
    django_allowed_hosts: str = Field(default="127.0.0.1,localhost")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance to avoid repeated environment parsing."""

    return AppSettings()
