from __future__ import annotations

from dataclasses import dataclass

from ikea_agent.chat.runtime import (
    build_google_embedding_settings,
    sync_milvus_from_snapshot_if_empty,
)


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
