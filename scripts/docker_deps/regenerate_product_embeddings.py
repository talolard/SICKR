"""Regenerate product embeddings at native Gemini width."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
from google import genai
from google.genai import types as genai_types
from pyarrow import parquet as pq

from ikea_agent.config import AppSettings, get_settings
from ikea_agent.shared.db_contract import PRODUCT_EMBEDDING_DIMENSIONS


@dataclass(frozen=True, slots=True)
class RegenerationSummary:
    """Observable result of one embedding parquet regeneration."""

    batch_size: int
    embedded_at: str
    embedding_dimensions: int
    input_path: str
    model_name: str
    output_path: str
    row_count: int
    run_id: str


def main() -> None:
    """Regenerate repo-local product embeddings with native Gemini width."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-path",
        default="data/parquet/product_embeddings",
    )
    parser.add_argument(
        "--output-path",
        default=None,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--retry-base-seconds",
        type=float,
        default=1.0,
    )
    args = parser.parse_args()

    settings = get_settings()
    input_path = Path(args.input_path).expanduser().resolve()
    output_path = (
        input_path if args.output_path is None else Path(args.output_path).expanduser().resolve()
    )
    summary = regenerate_product_embeddings(
        settings=settings,
        input_path=input_path,
        output_path=output_path,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        retry_base_seconds=args.retry_base_seconds,
    )
    print(json.dumps(asdict(summary), indent=2, sort_keys=True))


def regenerate_product_embeddings(
    *,
    settings: AppSettings,
    input_path: Path,
    output_path: Path,
    batch_size: int,
    max_retries: int,
    retry_base_seconds: float,
) -> RegenerationSummary:
    """Rewrite the embedding parquet with fresh native-width Gemini vectors."""

    if not settings.allow_model_requests:
        msg = "ALLOW_MODEL_REQUESTS must be enabled to regenerate product embeddings."
        raise RuntimeError(msg)
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    rows = _read_rows(input_path)
    client = _build_client(settings)
    embedded_at = datetime.now(tz=UTC)
    run_id = f"gemini-native-{embedded_at.strftime('%Y%m%d%H%M%S')}"

    for start in range(0, len(rows), batch_size):
        batch_rows = rows[start : start + batch_size]
        batch_texts = [_embedded_text(row) for row in batch_rows]
        vectors = _embed_many_with_retry(
            client=client,
            model_name=settings.gemini_model,
            texts=batch_texts,
            max_retries=max_retries,
            retry_base_seconds=retry_base_seconds,
        )
        for row, vector in zip(batch_rows, vectors, strict=True):
            row["embedding_model"] = settings.gemini_model
            row["embedding_vector"] = vector
            row["run_id"] = run_id
            row["embedded_at"] = embedded_at
        print(
            json.dumps(
                {
                    "done": start + len(batch_rows),
                    "row_count": len(rows),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    _write_rows(output_path=output_path, rows=rows)
    return RegenerationSummary(
        batch_size=batch_size,
        embedded_at=embedded_at.isoformat(),
        embedding_dimensions=PRODUCT_EMBEDDING_DIMENSIONS,
        input_path=str(input_path),
        model_name=settings.gemini_model,
        output_path=str(output_path),
        row_count=len(rows),
        run_id=run_id,
    )


def _build_client(settings: AppSettings) -> genai.Client:
    if settings.gemini_api_key:
        return genai.Client(api_key=settings.gemini_api_key)
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_region,
    )


def _embed_many_with_retry(
    *,
    client: genai.Client,
    model_name: str,
    texts: list[str],
    max_retries: int,
    retry_base_seconds: float,
) -> list[list[float]]:
    """Embed one batch with retry/backoff and strict width validation."""

    attempt = 0
    while True:
        try:
            response = client.models.embed_content(
                model=model_name,
                contents=texts,
                config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            embeddings = response.embeddings or []
            if len(embeddings) != len(texts):
                msg = (
                    "Gemini embedding response count mismatch: "
                    f"expected {len(texts)}, got {len(embeddings)}."
                )
                _raise_runtime_error(msg)
            vectors: list[list[float]] = []
            for item in embeddings:
                values = item.values or []
                if len(values) != PRODUCT_EMBEDDING_DIMENSIONS:
                    msg = (
                        "Gemini embedding width mismatch: "
                        f"expected {PRODUCT_EMBEDDING_DIMENSIONS}, got {len(values)}."
                    )
                    _raise_runtime_error(msg)
                vectors.append([float(value) for value in values])
        except Exception:
            attempt += 1
            if attempt > max_retries:
                raise
            time.sleep(retry_base_seconds * (2 ** (attempt - 1)))
        else:
            return vectors


def _embedded_text(row: dict[str, object]) -> str:
    value = row.get("embedded_text")
    if value is None:
        msg = (
            "Every embedding row must have `embedded_text` before regeneration. "
            f"Missing value for {row.get('canonical_product_key')}."
        )
        raise ValueError(msg)
    text = str(value).strip()
    if not text:
        msg = f"Embedded text is empty for {row.get('canonical_product_key')}."
        raise ValueError(msg)
    return text


def _raise_runtime_error(message: str) -> None:
    raise RuntimeError(message)


def _read_rows(input_path: Path) -> list[dict[str, object]]:
    table = pq.read_table(input_path)
    return [dict(row) for row in table.to_pylist() if isinstance(row, dict)]


def _write_rows(*, output_path: Path, rows: list[dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    pq.write_table(pa.Table.from_pylist(rows), temp_path)
    temp_path.replace(output_path)


if __name__ == "__main__":
    main()
