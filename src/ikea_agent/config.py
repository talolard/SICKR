"""Application settings model and config helpers.

Settings are read from environment variables so local `.env`, shell values,
and CI values can be layered in a predictable order.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

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
    gemini_generation_model: str = Field(default="gemini-3.1-flash-lite-preview")
    embedding_provider: str = Field(default="pydantic_ai_google")
    embedding_model_uri: str = Field(default="google-gla:gemini-embedding-001")
    gemini_api_key: str | None = Field(default=None)

    ikea_raw_csv_path: str = Field(default="data/IKEA_product_catalog.csv")
    duckdb_path: str = Field(default="data/ikea.duckdb")
    default_query_limit: int = Field(default=25, ge=1, le=200)
    default_market: str = Field(default="Germany")

    embedding_dimensions: int = Field(default=256, ge=64, le=3072)
    retrieval_candidate_limit: int = Field(default=250, ge=50, le=2000)

    milvus_lite_uri: str = Field(default="data/milvus_lite.db")
    milvus_collection: str = Field(default="ikea_product_embeddings")

    rerank_enabled: bool = Field(default=True)
    rerank_backend: Literal["lexical", "transformer"] = Field(default="transformer")
    rerank_candidate_limit: int = Field(default=100, ge=10, le=500)
    rerank_model_name: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance to avoid repeated environment parsing."""

    return AppSettings()
