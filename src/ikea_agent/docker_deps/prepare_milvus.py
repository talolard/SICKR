"""Prepare the shared Milvus collection from seeded Postgres embeddings."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, text

from ikea_agent.config import get_settings
from ikea_agent.retrieval.catalog_repository import EmbeddingSnapshotRepository
from ikea_agent.retrieval.service import MilvusAccessService
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url


@dataclass(frozen=True, slots=True)
class MilvusPrepareSummary:
    """Observable outcome of one shared-Milvus prepare run."""

    seed_version: str
    row_count: int
    collection_name: str
    state_file: str
    skipped: bool


def main() -> None:
    """Prepare the shared Milvus dependency from seeded Postgres data."""

    parser = argparse.ArgumentParser(description="Prepare the shared Milvus collection.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    database_url = resolve_database_url(
        database_url=args.database_url or settings.database_url,
        duckdb_path=settings.duckdb_path,
    )
    engine = create_database_engine(database_url)
    summary = prepare_shared_milvus(
        engine=engine,
        state_file=Path(args.state_file).expanduser().resolve(),
        force=args.force,
    )
    print(json.dumps(asdict(summary), indent=2, sort_keys=True))


def prepare_shared_milvus(
    *,
    engine: Engine,
    state_file: Path,
    force: bool,
) -> MilvusPrepareSummary:
    """Hydrate the shared Milvus collection from seeded Postgres embeddings."""

    settings = get_settings()
    seed_version = _read_catalog_seed_version(engine)
    if seed_version is None:
        msg = "Postgres catalog seed metadata is missing; seed Postgres before preparing Milvus."
        raise RuntimeError(msg)
    milvus_service = MilvusAccessService(settings)
    if not force and state_file.exists():
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        if (
            isinstance(loaded, dict)
            and loaded.get("seed_version") == seed_version
            and milvus_service.row_count() > 0
        ):
            return MilvusPrepareSummary(
                seed_version=seed_version,
                row_count=milvus_service.row_count(),
                collection_name=settings.milvus_collection,
                state_file=str(state_file),
                skipped=True,
            )

    repository = EmbeddingSnapshotRepository(engine)
    rows = repository.read_embedding_rows(embedding_model=settings.gemini_model)
    milvus_service.upsert_rows(rows)

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "seed_version": seed_version,
                "row_count": len(rows),
                "collection_name": settings.milvus_collection,
                "embedding_model": settings.gemini_model,
                "updated_at": datetime.now(tz=UTC).isoformat(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return MilvusPrepareSummary(
        seed_version=seed_version,
        row_count=len(rows),
        collection_name=settings.milvus_collection,
        state_file=str(state_file),
        skipped=False,
    )


def _read_catalog_seed_version(engine: Engine) -> str | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT version
                FROM ops.seed_state
                WHERE system_name = 'postgres_catalog'
                """
            )
        ).fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])


if __name__ == "__main__":
    main()
