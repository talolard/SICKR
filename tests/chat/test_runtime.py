from __future__ import annotations

import pytest

from ikea_agent.chat import runtime as runtime_module
from ikea_agent.chat.runtime import (
    build_google_embedding_settings,
    resolve_reranker_backend,
)
from ikea_agent.config import AppSettings


def test_google_embedding_settings_use_retrieval_query_task_type() -> None:
    settings = build_google_embedding_settings(dimensions=768)

    assert settings["dimensions"] == 768
    assert settings["google_task_type"] == "RETRIEVAL_QUERY"


def test_resolve_reranker_backend_uses_identity_when_disabled() -> None:
    settings = AppSettings(rerank_enabled=False, rerank_backend="transformer")

    assert resolve_reranker_backend(settings) == "identity"


def test_resolve_reranker_backend_uses_configured_backend_when_enabled() -> None:
    settings = AppSettings(rerank_enabled=True, rerank_backend="lexical")

    assert resolve_reranker_backend(settings) == "lexical"


def test_build_chat_runtime_uses_prepared_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AppSettings(
        database_url="postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent",
        ikea_image_catalog_root_dir="data/image-catalog",
        rerank_enabled=False,
    )
    engine = object()
    session_factory = object()
    catalog_repository = object()
    reranker = object()

    monkeypatch.setattr(runtime_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        runtime_module,
        "resolve_database_url",
        lambda *, database_url: database_url,
    )

    def _create_database_engine(_url: str, *, pool_mode: str = "queuepool") -> object:
        assert pool_mode == settings.database_pool_mode
        return engine

    monkeypatch.setattr(runtime_module, "create_database_engine", _create_database_engine)
    monkeypatch.setattr(runtime_module, "create_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(
        runtime_module,
        "build_google_embedding_settings",
        lambda *, dimensions: {"dimensions": dimensions},
    )

    class _EmbedderStub:
        def __init__(self, model_uri: str, *, settings: object) -> None:
            assert model_uri == settings_.embedding_model_uri
            assert settings == {"dimensions": settings_.embedding_dimensions}

    settings_ = settings
    monkeypatch.setattr(runtime_module, "Embedder", _EmbedderStub)
    monkeypatch.setattr(runtime_module, "resolve_reranker_backend", lambda _settings: "identity")
    monkeypatch.setattr(runtime_module, "CatalogRepository", lambda _engine: catalog_repository)
    monkeypatch.setattr(
        runtime_module,
        "get_reranker",
        lambda _backend, _runtime_settings: reranker,
    )

    runtime = runtime_module.build_chat_runtime()

    assert runtime.settings is settings
    assert runtime.sqlalchemy_engine is engine
    assert runtime.session_factory is session_factory
    assert runtime.catalog_repository is catalog_repository
    assert runtime.reranker is reranker
    assert tuple(runtime.__dataclass_fields__) == (
        "settings",
        "sqlalchemy_engine",
        "session_factory",
        "embedder",
        "catalog_repository",
        "reranker",
    )
