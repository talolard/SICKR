"""Generate minimal parquet fixtures for migration validation.

The migration stairway lane should verify Alembic behavior and seeded runtime
table shape without depending on Git LFS-backed canonical parquet artifacts.
This script writes a tiny deterministic fixture tree with the same logical path
layout as the production seed inputs so CI can seed a disposable Postgres
instance from valid parquet files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ikea_agent.shared.db_contract import PRODUCT_EMBEDDING_DIMENSIONS


def main() -> None:
    """Parse CLI arguments and materialize one disposable fixture repo tree."""

    parser = argparse.ArgumentParser(
        description="Write minimal parquet fixtures for migration validation."
    )
    parser.add_argument(
        "output_root",
        type=Path,
        help="Directory that will receive data/parquet fixture content.",
    )
    args = parser.parse_args()

    output_root = args.output_root.expanduser().resolve()
    write_fixture_repo(output_root=output_root)


def write_fixture_repo(*, output_root: Path) -> None:
    """Write deterministic products and embeddings parquet under one repo root."""

    products_root = output_root / "data" / "parquet" / "products_canonical"
    embeddings_root = output_root / "data" / "parquet" / "product_embeddings"
    products_root.mkdir(parents=True, exist_ok=True)
    embeddings_root.mkdir(parents=True, exist_ok=True)

    pq.write_table(_products_table(), products_root / "part-000.parquet")
    pq.write_table(_embeddings_table(), embeddings_root / "part-000.parquet")


def _products_table() -> pa.Table:
    rows = [
        {
            "canonical_product_key": "10018194-DE",
            "product_id": "10018194",
            "unique_id": "10018194-DE",
            "country": "Germany",
            "product_name": "Fixture Chair",
            "product_type": "chair",
            "description_text": "A migration validation fixture chair.",
            "main_category": "Seating",
            "sub_category": "Dining chairs",
            "dimensions_text": "45x52x80 cm",
            "width_cm": 45.0,
            "depth_cm": 52.0,
            "height_cm": 80.0,
            "price_eur": 79.99,
            "currency": "EUR",
            "rating": 4.6,
            "rating_count": 42,
            "badge": None,
            "online_sellable": True,
            "url": "https://example.test/products/10018194",
            "source_updated_at": "2026-03-19T00:00:00+00:00",
        },
        {
            "canonical_product_key": "100467-DE",
            "product_id": "100467",
            "unique_id": "100467-DE",
            "country": "Germany",
            "product_name": "Fixture Lamp",
            "product_type": "lamp",
            "description_text": "A migration validation fixture lamp.",
            "main_category": "Lighting",
            "sub_category": "Table lamps",
            "dimensions_text": "18x18x42 cm",
            "width_cm": 18.0,
            "depth_cm": 18.0,
            "height_cm": 42.0,
            "price_eur": 39.99,
            "currency": "EUR",
            "rating": 4.3,
            "rating_count": 17,
            "badge": None,
            "online_sellable": True,
            "url": "https://example.test/products/100467",
            "source_updated_at": "2026-03-19T00:00:00+00:00",
        },
    ]
    return pa.Table.from_pylist(rows)


def _embeddings_table() -> pa.Table:
    vector_a = [0.01] * PRODUCT_EMBEDDING_DIMENSIONS
    vector_b = [0.02] * PRODUCT_EMBEDDING_DIMENSIONS
    rows = [
        {
            "canonical_product_key": "10018194-DE",
            "embedding_model": "text-embedding-3-small",
            "run_id": "ci-fixture",
            "embedding_vector": vector_a,
            "embedded_text": "Fixture Chair",
            "embedded_at": "2026-03-19T00:00:00+00:00",
        },
        {
            "canonical_product_key": "100467-DE",
            "embedding_model": "text-embedding-3-small",
            "run_id": "ci-fixture",
            "embedding_vector": vector_b,
            "embedded_text": "Fixture Lamp",
            "embedded_at": "2026-03-19T00:00:00+00:00",
        },
    ]
    return pa.Table.from_pylist(rows)


if __name__ == "__main__":
    main()
