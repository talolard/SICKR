"""Generate evaluation query candidates with Gemini structured outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel, Field

from tal_maria_ikea.config import AppSettings, get_settings
from tal_maria_ikea.eval.repository import EvalRepository
from tal_maria_ikea.ingest.embedding_client import EmbeddingClientConfig, build_generation_client
from tal_maria_ikea.logging_config import configure_logging, get_logger
from tal_maria_ikea.shared.db import connect_db, run_sql_file


class GeneratedQuery(BaseModel):
    """Structured generated query row from Gemini response."""

    query_text: str = Field(min_length=3)
    category_hint: str | None = None
    intent_kind: str | None = None


class GeneratedQueryResponse(BaseModel):
    """Top-level response contract for generated query list."""

    queries: list[GeneratedQuery]


@dataclass(frozen=True, slots=True)
class GenerateOptions:
    """CLI options for eval query generation command."""

    subset_id: str
    prompt_version: str
    target_count: int
    batch_size: int
    parallelism: int
    max_rounds: int


def run_generate(options: GenerateOptions) -> int:
    """Generate and persist evaluation queries with provenance metadata."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger = get_logger("eval.generate")

    connection = connect_db(settings.duckdb_path)
    run_sql_file(connection, "sql/10_schema.sql")
    run_sql_file(connection, "sql/41_eval_registry.sql")
    repository = EvalRepository(connection)

    subset_definition = f"market=Germany;target_count={options.target_count}"
    subset_hash = hashlib.sha256(subset_definition.encode("utf-8")).hexdigest()
    repository.upsert_subset(options.subset_id, subset_definition, subset_hash)

    prompt_text = _build_prompt(
        batch_size=options.batch_size,
        prompt_version=options.prompt_version,
        round_index=0,
        request_index=0,
    )
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    repository.upsert_prompt(options.prompt_version, prompt_text, prompt_hash)
    logger.info(
        "eval_generation_start",
        subset_id=options.subset_id,
        prompt_version=options.prompt_version,
        target_count=options.target_count,
        batch_size=options.batch_size,
        parallelism=options.parallelism,
        max_rounds=options.max_rounds,
    )

    generated: dict[str, GeneratedQuery] = {}
    total_raw_count = 0
    for round_index in range(options.max_rounds):
        remaining = options.target_count - len(generated)
        if remaining <= 0:
            break

        request_sizes = _plan_round_requests(
            remaining=remaining,
            batch_size=options.batch_size,
            parallelism=options.parallelism,
        )
        logger.info(
            "eval_generation_round_start",
            round_index=round_index + 1,
            remaining=remaining,
            request_count=len(request_sizes),
            request_sizes=request_sizes,
        )

        with ThreadPoolExecutor(max_workers=options.parallelism) as executor:
            futures = [
                executor.submit(
                    _generate_batch,
                    settings=settings,
                    batch_size=request_size,
                    prompt_version=options.prompt_version,
                    round_index=round_index,
                    request_index=request_index,
                )
                for request_index, request_size in enumerate(request_sizes)
            ]
            for future in as_completed(futures):
                batch = future.result()
                total_raw_count += len(batch)
                for item in batch:
                    dedupe_key = _normalize_query_text(item.query_text)
                    if dedupe_key not in generated:
                        generated[dedupe_key] = item
                logger.info(
                    "eval_generation_batch_complete",
                    round_index=round_index + 1,
                    batch_raw_count=len(batch),
                    unique_generated=len(generated),
                )

        logger.info(
            "eval_generation_round_complete",
            round_index=round_index + 1,
            unique_generated=len(generated),
            raw_generated=total_raw_count,
            remaining=max(0, options.target_count - len(generated)),
        )

    if len(generated) < options.target_count:
        message = (
            "Generated unique eval queries below target after max rounds. "
            f"Generated={len(generated)}, target={options.target_count}, "
            f"max_rounds={options.max_rounds}."
        )
        raise RuntimeError(message)

    selected_queries = list(generated.values())[: options.target_count]
    rows = [
        (str(uuid4()), item.query_text, item.category_hint, item.intent_kind)
        for item in selected_queries
    ]
    repository.insert_generated_queries(options.prompt_version, options.subset_id, rows)

    logger.info(
        "generated_eval_queries",
        subset_id=options.subset_id,
        prompt_version=options.prompt_version,
        generated_count=len(rows),
        raw_generated_count=total_raw_count,
    )
    print(json.dumps({"generated_count": len(rows)}, indent=2))
    return len(rows)


def _generate_batch(
    settings: AppSettings,
    batch_size: int,
    prompt_version: str,
    round_index: int,
    request_index: int,
) -> list[GeneratedQuery]:
    client = build_generation_client(
        EmbeddingClientConfig(
            project_id=settings.gcp_project_id,
            location=settings.gcp_region,
            model_name=settings.gemini_model,
            api_key=settings.gemini_api_key,
        )
    )
    prompt_text = _build_prompt(
        batch_size=batch_size,
        prompt_version=prompt_version,
        round_index=round_index,
        request_index=request_index,
    )
    response = client.models.generate_content(
        model=settings.gemini_generation_model,
        contents=prompt_text,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": GeneratedQueryResponse.model_json_schema(),
        },
    )
    if response.text is None:
        message = "Gemini response did not include JSON text payload."
        raise RuntimeError(message)
    parsed = GeneratedQueryResponse.model_validate_json(response.text)
    return parsed.queries[:batch_size]


def _build_prompt(
    batch_size: int, prompt_version: str, round_index: int, request_index: int
) -> str:
    return (
        "Generate natural-language IKEA shopping search queries for semantic retrieval. "
        "Return concise user-style search text. Include categories such as storage, sofas, "
        "lighting, desks, beds, and dining furniture. Include dimensions and style intents "
        "where useful. Avoid duplicates. "
        f"Return exactly {batch_size} items. "
        f"Prompt version: {prompt_version}. "
        f"Batch round: {round_index + 1}. Request: {request_index + 1}."
    )


def _normalize_query_text(query_text: str) -> str:
    return " ".join(query_text.strip().lower().split())


def _plan_round_requests(remaining: int, batch_size: int, parallelism: int) -> list[int]:
    if remaining <= 0:
        return []
    request_count = min(parallelism, math.ceil(remaining / batch_size))
    sizes = [batch_size] * request_count
    overflow = (request_count * batch_size) - remaining
    if overflow > 0:
        sizes[-1] = max(1, batch_size - overflow)
    return sizes


def _parse_args() -> GenerateOptions:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Generate evaluation query candidates via Gemini.")
    parser.add_argument("--subset-id", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--target-count", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=settings.eval_generation_batch_size)
    parser.add_argument("--parallelism", type=int, default=settings.eval_generation_parallelism)
    parser.add_argument("--max-rounds", type=int, default=settings.eval_generation_max_rounds)
    args = parser.parse_args()

    if args.target_count < 1:
        raise ValueError("--target-count must be >= 1")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be >= 1")
    if args.parallelism < 1:
        raise ValueError("--parallelism must be >= 1")
    if args.max_rounds < 1:
        raise ValueError("--max-rounds must be >= 1")

    return GenerateOptions(
        subset_id=args.subset_id,
        prompt_version=args.prompt_version,
        target_count=args.target_count,
        batch_size=args.batch_size,
        parallelism=args.parallelism,
        max_rounds=args.max_rounds,
    )


if __name__ == "__main__":
    run_generate(_parse_args())
