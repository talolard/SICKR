from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from ikea_agent.chat import runtime as runtime_module
from ikea_agent.chat.runtime import (
    build_google_embedding_settings,
    resolve_reranker_backend,
    sync_milvus_from_snapshot_if_empty,
)
from ikea_agent.config import AppSettings


def test_google_embedding_settings_use_retrieval_query_task_type() -> None:
    settings = build_google_embedding_settings(dimensions=768)

    assert settings["dimensions"] == 768
    assert settings["google_task_type"] == "RETRIEVAL_QUERY"


@dataclass
class _RepositoryStub:
    rows: list[tuple[str, str, tuple[float, ...]]]
    calls: int = 0

    def read_embedding_rows(
        self,
        *,
        embedding_model: str,
    ) -> list[tuple[str, str, tuple[float, ...]]]:
        self.calls += 1
        _ = embedding_model
        return self.rows


@dataclass
class _MilvusStub:
    current_row_count: int
    upserted_rows: list[tuple[str, str, tuple[float, ...]]] | None = None

    def row_count(self) -> int:
        return self.current_row_count

    def upsert_rows(self, rows: list[tuple[str, str, tuple[float, ...]]]) -> None:
        self.upserted_rows = rows
        self.current_row_count = len(rows)


def test_sync_milvus_from_snapshot_if_empty_hydrates_when_empty() -> None:
    repository = _RepositoryStub(rows=[("abc", "gemini-embedding-001", (0.1, 0.2, 0.3))])
    milvus = _MilvusStub(current_row_count=0)

    inserted = sync_milvus_from_snapshot_if_empty(
        repository=repository,
        milvus_service=milvus,
        embedding_model="gemini-embedding-001",
    )

    assert inserted == 1
    assert repository.calls == 1
    assert milvus.upserted_rows is not None


def test_sync_milvus_from_snapshot_if_empty_skips_when_populated() -> None:
    repository = _RepositoryStub(rows=[("abc", "gemini-embedding-001", (0.1,))])
    milvus = _MilvusStub(current_row_count=12)

    inserted = sync_milvus_from_snapshot_if_empty(
        repository=repository,
        milvus_service=milvus,
        embedding_model="gemini-embedding-001",
    )

    assert inserted == 0
    assert repository.calls == 0
    assert milvus.upserted_rows is None


def test_resolve_reranker_backend_uses_identity_when_disabled() -> None:
    settings = AppSettings(rerank_enabled=False, rerank_backend="transformer")

    assert resolve_reranker_backend(settings) == "identity"


def test_resolve_reranker_backend_uses_configured_backend_when_enabled() -> None:
    settings = AppSettings(rerank_enabled=True, rerank_backend="lexical")

    assert resolve_reranker_backend(settings) == "lexical"


def test_build_chat_runtime_backfills_display_titles_during_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AppSettings(
        duckdb_path="data/test.duckdb",
        ikea_image_catalog_root_dir="data/image-catalog",
        rerank_enabled=False,
    )
    engine = object()
    session_factory = object()
    snapshot_repository = object()
    catalog_repository = object()
    reranker = object()
    product_image_catalog = object()
    backfill_calls: list[object] = []
    ensure_collection_calls: list[bool] = []
    sync_calls: list[dict[str, object]] = []

    monkeypatch.setattr(runtime_module, "get_settings", lambda: settings)
    monkeypatch.setattr(runtime_module, "create_duckdb_engine", lambda _path: engine)
    monkeypatch.setattr(runtime_module, "create_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(runtime_module, "ensure_runtime_schema", lambda _engine: None)
    monkeypatch.setattr(
        runtime_module,
        "backfill_product_display_titles",
        lambda _engine: backfill_calls.append(engine) or 0,
    )
    monkeypatch.setattr(
        runtime_module,
        "EmbeddingSnapshotRepository",
        lambda _engine: snapshot_repository,
    )
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

    class _MilvusStub:
        def __init__(self, runtime_settings: AppSettings) -> None:
            assert runtime_settings is settings_

        def ensure_collection(self) -> None:
            ensure_collection_calls.append(True)

    monkeypatch.setattr(runtime_module, "MilvusAccessService", _MilvusStub)
    monkeypatch.setattr(
        runtime_module,
        "sync_milvus_from_snapshot_if_empty",
        lambda **kwargs: sync_calls.append(kwargs) or 0,
    )
    monkeypatch.setattr(runtime_module, "resolve_reranker_backend", lambda _settings: "identity")
    monkeypatch.setattr(runtime_module, "CatalogRepository", lambda _engine: catalog_repository)
    monkeypatch.setattr(
        runtime_module,
        "get_reranker",
        lambda _backend, _runtime_settings: reranker,
    )

    def _from_output_root(*, output_root: object) -> object:
        assert output_root is not None
        return product_image_catalog

    monkeypatch.setattr(
        runtime_module,
        "ProductImageCatalog",
        SimpleNamespace(from_output_root=_from_output_root),
    )

    runtime = runtime_module.build_chat_runtime()

    assert runtime.settings is settings
    assert runtime.sqlalchemy_engine is engine
    assert runtime.session_factory is session_factory
    assert runtime.catalog_repository is catalog_repository
    assert runtime.reranker is reranker
    assert runtime.product_image_catalog is product_image_catalog
    assert backfill_calls == [engine]
    assert ensure_collection_calls == [True]
    assert len(sync_calls) == 1
    assert sync_calls[0]["repository"] is snapshot_repository
    assert sync_calls[0]["embedding_model"] == settings.gemini_model
