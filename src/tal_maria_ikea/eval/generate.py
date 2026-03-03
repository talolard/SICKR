"""Generate evaluation query candidates with Gemini structured outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from uuid import uuid4

from google import genai
from pydantic import BaseModel, Field

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.eval.repository import EvalRepository
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

    prompt_text = (
        "Generate natural-language IKEA shopping search queries for semantic retrieval. "
        "Return concise user-style search text. Include categories such as storage, sofas, "
        "lighting, desks, and beds. Include dimensions and style intents where useful. "
        f"Return exactly {options.target_count} items."
    )
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    repository.upsert_prompt(options.prompt_version, prompt_text, prompt_hash)

    client = genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_region,
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
    rows = [
        (str(uuid4()), item.query_text, item.category_hint, item.intent_kind)
        for item in parsed.queries[: options.target_count]
    ]
    repository.insert_generated_queries(options.prompt_version, options.subset_id, rows)

    logger.info(
        "generated_eval_queries",
        subset_id=options.subset_id,
        prompt_version=options.prompt_version,
        generated_count=len(rows),
    )
    print(json.dumps({"generated_count": len(rows)}, indent=2))
    return len(rows)


def _parse_args() -> GenerateOptions:
    parser = argparse.ArgumentParser(description="Generate evaluation query candidates via Gemini.")
    parser.add_argument("--subset-id", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--target-count", type=int, default=200)
    args = parser.parse_args()

    return GenerateOptions(
        subset_id=args.subset_id,
        prompt_version=args.prompt_version,
        target_count=args.target_count,
    )


if __name__ == "__main__":
    run_generate(_parse_args())
