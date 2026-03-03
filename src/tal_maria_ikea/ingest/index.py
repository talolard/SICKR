"""CLI entrypoint for embedding index runs."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.ingest.embedding_client import (
    EmbeddingClientConfig,
    VertexGeminiEmbeddingClient,
)
from tal_maria_ikea.ingest.repository import IndexRepository
from tal_maria_ikea.ingest.text_strategy import select_embedding_input_view
from tal_maria_ikea.logging_config import configure_logging, get_logger
from tal_maria_ikea.shared.db import connect_db, run_sql_file
from tal_maria_ikea.shared.types import EmbeddedVectorRow, EmbeddingStrategyVersion


@dataclass(frozen=True, slots=True)
class IndexRunOptions:
    """Runtime options parsed from CLI arguments."""

    strategy: EmbeddingStrategyVersion
    subset_limit: int | None
    parallelism: int
    batch_size: int
    use_batch: bool


def _chunk_rows(rows: list[tuple[str, str]], chunk_size: int) -> Iterable[list[tuple[str, str]]]:
    """Yield fixed-size chunks from a list of key/text rows."""

    for start in range(0, len(rows), chunk_size):
        yield rows[start : start + chunk_size]


def run_indexing(options: IndexRunOptions) -> str:
    """Execute one embedding run and return the run identifier."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger = get_logger("ingest.index")

    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/14_market_views.sql")
    run_sql_file(connection, "sql/21_embedding_inputs.sql")

    repository = IndexRepository(connection)
    source_view = select_embedding_input_view(options.strategy)
    rows = repository.read_embedding_inputs(source_view, options.subset_limit)

    run_id = f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    repository.insert_run(
        run_id=run_id,
        scope="Germany",
        strategy_version=options.strategy,
        embedding_model=settings.gemini_model,
        provider=settings.embedding_provider,
        use_batch=options.use_batch,
        subset_limit=options.subset_limit,
        requested_parallelism=options.parallelism,
        total_records=len(rows),
    )

    if options.use_batch:
        logger.warning(
            "Batch mode is experimental in Phase 1; falling back to sync parallel execution.",
            run_id=run_id,
        )

    client = VertexGeminiEmbeddingClient(
        EmbeddingClientConfig(
            project_id=settings.gcp_project_id,
            location=settings.gcp_region,
            model_name=settings.gemini_model,
        )
    )

    embedded_rows: list[EmbeddedVectorRow] = []
    failed_records = 0

    with ThreadPoolExecutor(max_workers=options.parallelism) as executor:
        futures: list[Future[list[EmbeddedVectorRow]]] = [
            executor.submit(_embed_chunk, client, chunk, options.strategy)
            for chunk in _chunk_rows(rows, options.batch_size)
        ]

        for future in futures:
            try:
                embedded_rows.extend(future.result())
            except Exception as error:  # pragma: no cover - integration path
                failed_records += options.batch_size
                logger.exception("Chunk embedding failed", error=str(error), run_id=run_id)

    repository.upsert_embeddings(
        rows=embedded_rows,
        embedding_model=settings.gemini_model,
        run_id=run_id,
    )
    repository.mark_run_complete(
        run_id=run_id,
        embedded_records=len(embedded_rows),
        failed_records=failed_records,
    )

    logger.info(
        "Embedding run complete",
        run_id=run_id,
        total_records=len(rows),
        embedded_records=len(embedded_rows),
        failed_records=failed_records,
    )
    return run_id


def _embed_chunk(
    client: VertexGeminiEmbeddingClient,
    chunk: list[tuple[str, str]],
    strategy: EmbeddingStrategyVersion,
) -> list[EmbeddedVectorRow]:
    """Embed one chunk and return vector rows for persistence."""

    texts = [text for _, text in chunk]
    vectors = client.embed_many(texts)

    return [
        EmbeddedVectorRow(
            canonical_product_key=key,
            embedding_text=text,
            embedding_vector=vector,
            strategy_version=strategy,
        )
        for (key, text), vector in zip(chunk, vectors, strict=True)
    ]


def _parse_args() -> IndexRunOptions:
    """Parse CLI arguments for indexing execution."""

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run embedding index build for catalog rows.")
    parser.add_argument(
        "--strategy",
        default="v2_metadata_first",
        choices=["v1_baseline", "v2_metadata_first"],
    )
    parser.add_argument("--subset-limit", type=int, default=None)
    parser.add_argument("--parallelism", type=int, default=settings.embedding_parallelism)
    parser.add_argument("--batch-size", type=int, default=settings.embedding_batch_size)
    parser.add_argument("--use-batch", action="store_true")
    args = parser.parse_args()

    return IndexRunOptions(
        strategy=args.strategy,
        subset_limit=args.subset_limit,
        parallelism=args.parallelism,
        batch_size=args.batch_size,
        use_batch=args.use_batch,
    )


if __name__ == "__main__":
    run_indexing(_parse_args())
