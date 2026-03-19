"""Application settings model and config helpers.

Settings are read from environment variables so local `.env`, shell values,
and CI values can be layered in a predictable order.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ikea_agent.shared.db_contract import PRODUCT_EMBEDDING_DIMENSIONS


class AgentModelConfig(BaseModel):
    """Optional model override configuration for one named agent."""

    model: str | None = Field(default=None)


class AppSettings(BaseSettings):
    """Strongly typed runtime settings for local development and CI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_nested_delimiter="__",
    )

    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)
    logfire_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LOGFIRE_TOKEN", "APP_LOGFIRE_TOKEN"),
    )
    logfire_service_name: str = Field(default="ikea-agent")
    logfire_service_version: str | None = Field(default=None)
    logfire_environment: str | None = Field(default=None)
    logfire_send_mode: Literal["if-token-present", "always"] = Field(default="if-token-present")

    gcp_project_id: str = Field(default="gen-lang-client-0545732168")
    gcp_region: str = Field(default="us-central1")
    gemini_model: str = Field(default="gemini-embedding-001")
    gemini_generation_model: str = Field(default="gemini-3.1-flash-lite-preview")
    gemini_image_analysis_model: str = Field(default="gemini-2.5-flash")
    embedding_provider: str = Field(default="google-gla")
    embedding_model_uri: str = Field(default="google-gla:gemini-embedding-001")
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    allow_model_requests: bool = Field(
        default=True,
        validation_alias=AliasChoices("ALLOW_MODEL_REQUESTS", "APP_ALLOW_MODEL_REQUESTS"),
    )

    ikea_raw_csv_path: str = Field(default="data/IKEA_product_catalog.csv")
    database_url: str | None = Field(
        default="postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    duckdb_path: str | None = Field(default=None)
    artifact_root_dir: str = Field(default="data/artifacts")
    ikea_image_catalog_root_dir: str = Field(
        default="/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog"
    )
    ikea_image_catalog_run_id: str | None = Field(default=None)
    feedback_capture_enabled: bool = Field(default=False)
    feedback_root_dir: str = Field(default="comments")
    trace_capture_enabled: bool = Field(default=False)
    trace_root_dir: str = Field(default="traces")
    default_query_limit: int = Field(default=25, ge=1, le=200)

    embedding_dimensions: int = Field(
        default=PRODUCT_EMBEDDING_DIMENSIONS,
        ge=PRODUCT_EMBEDDING_DIMENSIONS,
        le=PRODUCT_EMBEDDING_DIMENSIONS,
    )
    retrieval_candidate_limit: int = Field(default=250, ge=50, le=2000)
    image_serving_strategy: Literal["backend_proxy", "direct_public_url"] = Field(
        default="backend_proxy"
    )
    image_service_base_url: str | None = Field(default=None)

    rerank_enabled: bool = Field(default=True)
    rerank_backend: Literal["lexical", "transformer"] = Field(default="lexical")
    rerank_model_name: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    mmr_lambda: float = Field(default=0.8, ge=0.0, le=1.0)
    mmr_preselect_limit: int = Field(default=30, ge=5, le=200)
    embedding_query_batch_size: int = Field(default=16, ge=1, le=256)
    embedding_neighbor_limit: int = Field(default=0, ge=0, le=10000)
    agents: dict[str, AgentModelConfig] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("agents", "subagents"),
    )

    def _resolve_agent_config(self, agent_name: str) -> AgentModelConfig | None:
        direct = self.agents.get(agent_name)
        if direct is not None:
            return direct
        lower = self.agents.get(agent_name.lower())
        if lower is not None:
            return lower
        return self.agents.get(agent_name.upper())

    def agent_model(self, agent_name: str) -> str | None:
        """Return configured model override for one agent when present."""

        resolved = self._resolve_agent_config(agent_name)
        if resolved and resolved.model:
            return resolved.model
        return None


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance to avoid repeated environment parsing."""

    return AppSettings()
