"""CLI entrypoint for embedding index runs."""

from __future__ import annotations

import argparse
import re
import secrets
import threading
import time
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
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
    build_vss_index: bool


class _RequestRateLimiter:
    """Thread-safe request pacing helper to cap requests per minute."""

    def __init__(self, requests_per_minute: int) -> None:
        self._min_interval_seconds = 60.0 / float(requests_per_minute)
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait_turn(self) -> None:
        """Sleep until the next request slot is available."""

        with self._lock:
            now = time.monotonic()
            wait_seconds = max(0.0, self._next_allowed_at - now)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
                now = time.monotonic()
            self._next_allowed_at = now + self._min_interval_seconds


def _chunk_rows(rows: list[tuple[str, str]], chunk_size: int) -> Iterable[list[tuple[str, str]]]:
    """Yield fixed-size chunks from a list of key/text rows."""

    for start in range(0, len(rows), chunk_size):
        yield rows[start : start + chunk_size]


def run_indexing(options: IndexRunOptions) -> str:  # noqa: PLR0915
    """Execute one embedding run and return the run identifier."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger = get_logger("ingest.index")

    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/14_market_views.sql")
    run_sql_file(connection, "sql/21_embedding_inputs.sql")

    repository = IndexRepository(connection)
    schema_vector_dimensions = repository.embedding_vector_dimensions()
    if schema_vector_dimensions != settings.embedding_dimensions:
        message = (
            "Embedding dimension mismatch: "
            f"database schema uses FLOAT[{schema_vector_dimensions}] but "
            f"EMBEDDING_DIMENSIONS={settings.embedding_dimensions}. "
            "Run `make db-reset` (recommended for this greenfield project) "
            "or align EMBEDDING_DIMENSIONS to the database schema."
        )
        raise RuntimeError(message)

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

    logger.info(
        "Embedding input rows loaded",
        run_id=run_id,
        row_count=len(rows),
        strategy=options.strategy,
        batch_size=options.batch_size,
        parallelism=options.parallelism,
        use_batch_flag=options.use_batch,
    )
    logger.info(
        "Embedding API mode",
        run_id=run_id,
        mode="sync_embed_content_multi_item",
        note=(
            "Gemini may log this as batchEmbedContents HTTP calls even though "
            "the async batch job API is not being used."
        ),
    )

    if options.use_batch:
        logger.warning(
            "Asynchronous batch API mode is not implemented yet; "
            "using synchronous multi-item requests.",
            run_id=run_id,
        )

    client = VertexGeminiEmbeddingClient(
        EmbeddingClientConfig(
            project_id=settings.gcp_project_id,
            location=settings.gcp_region,
            model_name=settings.gemini_model,
            api_key=settings.gemini_api_key,
            output_dimensions=settings.embedding_dimensions,
        )
    )

    embedded_rows: list[EmbeddedVectorRow] = []
    failed_records = 0
    rate_limiter = _RequestRateLimiter(settings.embedding_requests_per_minute)
    logger.info(
        "Embedding request throttling configured",
        run_id=run_id,
        requests_per_minute=settings.embedding_requests_per_minute,
    )

    with ThreadPoolExecutor(max_workers=options.parallelism) as executor:
        future_sizes: dict[Future[list[EmbeddedVectorRow]], int] = {}
        for chunk_index, chunk in enumerate(_chunk_rows(rows, options.batch_size), start=1):
            future = executor.submit(
                _embed_chunk_with_retry,
                client,
                chunk,
                options.strategy,
                logger,
                run_id,
                chunk_index,
                settings.embedding_max_retries,
                settings.embedding_retry_base_seconds,
                settings.embedding_retry_max_seconds,
                settings.embedding_retry_jitter_seconds,
                rate_limiter,
            )
            future_sizes[future] = len(chunk)

        for future in as_completed(future_sizes):
            try:
                chunk_rows = future.result()
                embedded_rows.extend(chunk_rows)
                logger.info(
                    "Embedding chunk complete",
                    run_id=run_id,
                    chunk_size=len(chunk_rows),
                    embedded_so_far=len(embedded_rows),
                    total_rows=len(rows),
                )
            except Exception as error:  # pragma: no cover - integration path
                failed_records += future_sizes[future]
                logger.exception("Chunk embedding failed", error=str(error), run_id=run_id)

    logger.info(
        "Embedding API phase complete",
        run_id=run_id,
        embedded_records=len(embedded_rows),
        failed_records=failed_records,
    )

    logger.info("Dropping existing HNSW index before upsert", run_id=run_id)
    repository.drop_vss_hnsw_index_if_exists()
    logger.info(
        "Starting embedding upsert",
        run_id=run_id,
        row_count=len(embedded_rows),
        upsert_chunk_size=settings.embedding_upsert_chunk_size,
    )
    upserted_records = 0
    for chunk_index, start in enumerate(
        range(0, len(embedded_rows), settings.embedding_upsert_chunk_size), start=1
    ):
        chunk_rows = embedded_rows[start : start + settings.embedding_upsert_chunk_size]
        logger.info(
            "Embedding upsert chunk start",
            run_id=run_id,
            chunk_index=chunk_index,
            chunk_size=len(chunk_rows),
        )
        repository.upsert_embeddings(
            rows=chunk_rows,
            embedding_model=settings.gemini_model,
            run_id=run_id,
            vector_dimensions=settings.embedding_dimensions,
            chunk_size=settings.embedding_upsert_chunk_size,
        )
        upserted_records += len(chunk_rows)
        logger.info(
            "Embedding upsert progress",
            run_id=run_id,
            upserted_records=upserted_records,
            total_records=len(embedded_rows),
        )
    logger.info("Embedding upsert complete", run_id=run_id, row_count=upserted_records)
    repository.mark_run_complete(
        run_id=run_id,
        embedded_records=len(embedded_rows),
        failed_records=failed_records,
    )

    if options.build_vss_index:
        logger.info("Building HNSW index", run_id=run_id, metric=settings.vss_metric)
        repository.create_vss_hnsw_index(metric=settings.vss_metric)
        logger.info("vss_hnsw_index_ready", run_id=run_id, metric=settings.vss_metric)

    logger.info(
        "Embedding run complete",
        run_id=run_id,
        total_records=len(rows),
        embedded_records=len(embedded_rows),
        failed_records=failed_records,
    )
    return run_id


def _embed_chunk_with_retry(
    client: VertexGeminiEmbeddingClient,
    chunk: list[tuple[str, str]],
    strategy: EmbeddingStrategyVersion,
    logger: object,
    run_id: str,
    chunk_index: int,
    max_retries: int,
    base_seconds: float,
    max_seconds: float,
    jitter_seconds: float,
    rate_limiter: _RequestRateLimiter,
) -> list[EmbeddedVectorRow]:
    """Embed one chunk with retry/backoff and return vector rows for persistence."""

    attempt = 1
    while True:
        try:
            rate_limiter.wait_turn()
            texts = [text for _, text in chunk]
            vectors = client.embed_many(texts)
            _validate_vector_count(
                chunk_index=chunk_index, expected=len(chunk), actual=len(vectors)
            )

            return [
                EmbeddedVectorRow(
                    canonical_product_key=key,
                    embedding_text=text,
                    embedding_vector=vector,
                    strategy_version=strategy,
                )
                for (key, text), vector in zip(chunk, vectors, strict=True)
            ]
        except Exception as error:
            if attempt > max_retries:
                raise
            retry_hint = _extract_retry_delay_seconds(str(error))
            backoff = _compute_backoff_seconds(
                attempt=attempt,
                retry_hint=retry_hint,
                base_seconds=base_seconds,
                max_seconds=max_seconds,
                jitter_seconds=jitter_seconds,
            )
            _log_retry(
                logger=logger,
                run_id=run_id,
                chunk_index=chunk_index,
                attempt=attempt,
                max_retries=max_retries,
                backoff_seconds=backoff,
                retry_hint=retry_hint,
                error=error,
            )
            time.sleep(backoff)
            attempt += 1


def _extract_retry_delay_seconds(error_message: str) -> float | None:
    """Parse retry delay seconds from provider error message when available."""

    direct_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_message, re.IGNORECASE)
    if direct_match:
        return float(direct_match.group(1))

    detail_match = re.search(r"retryDelay['\"]:\s*['\"]([0-9]+)s['\"]", error_message)
    if detail_match:
        return float(detail_match.group(1))

    return None


def _compute_backoff_seconds(
    attempt: int,
    retry_hint: float | None,
    base_seconds: float,
    max_seconds: float,
    jitter_seconds: float,
) -> float:
    """Compute bounded exponential backoff with optional provider retry hint."""

    exponential = base_seconds * (2 ** (attempt - 1))
    target = max(exponential, retry_hint or 0.0)
    bounded = min(max_seconds, target)
    if jitter_seconds <= 0:
        return bounded
    return bounded + secrets.SystemRandom().uniform(0.0, jitter_seconds)


def _log_retry(
    logger: object,
    run_id: str,
    chunk_index: int,
    attempt: int,
    max_retries: int,
    backoff_seconds: float,
    retry_hint: float | None,
    error: Exception,
) -> None:
    """Emit retry scheduling details to make rate-limit behavior observable."""

    if hasattr(logger, "warning"):
        logger.warning(
            "Chunk embedding retry scheduled",
            run_id=run_id,
            chunk_index=chunk_index,
            attempt=attempt,
            max_retries=max_retries,
            backoff_seconds=round(backoff_seconds, 3),
            retry_hint_seconds=retry_hint,
            error=str(error),
        )


def _validate_vector_count(chunk_index: int, expected: int, actual: int) -> None:
    """Ensure embedding response count matches request chunk size."""

    if expected == actual:
        return
    message = (
        f"Embedding result count mismatch for chunk {chunk_index}: expected {expected} got {actual}"
    )
    raise RuntimeError(message)


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
    parser.add_argument("--build-vss-index", action="store_true", default=settings.vss_build_index)
    args = parser.parse_args()

    return IndexRunOptions(
        strategy=args.strategy,
        subset_limit=args.subset_limit,
        parallelism=args.parallelism,
        batch_size=args.batch_size,
        use_batch=args.use_batch,
        build_vss_index=args.build_vss_index,
    )


if __name__ == "__main__":
    run_indexing(_parse_args())
