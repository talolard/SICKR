from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, insert

from ikea_agent.retrieval.schema import product_embeddings, product_images, products_canonical
from ikea_agent.shared.db_contract import (
    IMAGE_CATALOG_SEED_SYSTEM,
    POSTGRES_SEED_SYSTEM,
    REMOTE_IMAGE_STORAGE_BACKEND,
)
from ikea_agent.shared.ops_schema import seed_state


def insert_ready_seed_data(
    engine: Engine,
    *,
    public_url: str
    | None = "https://designagent.talperry.com/static/product-images/test-image.jpg",
) -> None:
    """Insert the minimum seed rows and catalog data required by deploy checks."""

    with engine.begin() as connection:
        connection.execute(
            insert(seed_state),
            [
                {
                    "system_name": POSTGRES_SEED_SYSTEM,
                    "version": "seed-v1",
                    "source_kind": "test",
                    "status": "ready",
                    "details_json": "{}",
                    "updated_at": datetime(2026, 3, 25, tzinfo=UTC),
                },
                {
                    "system_name": IMAGE_CATALOG_SEED_SYSTEM,
                    "version": "seed-v1",
                    "source_kind": "test",
                    "status": "ready",
                    "details_json": "{}",
                    "updated_at": datetime(2026, 3, 25, tzinfo=UTC),
                },
            ],
        )
        connection.execute(
            insert(products_canonical),
            [
                {
                    "canonical_product_key": "product-1",
                    "product_id": 1001,
                    "country": "Germany",
                    "product_name": "Test product",
                    "display_title": "Test product",
                }
            ],
        )
        connection.execute(
            insert(product_embeddings),
            [
                {
                    "canonical_product_key": "product-1",
                    "embedding_model": "test-model",
                    "run_id": "test-run",
                    "embedding_vector": [0.1, 0.2, 0.3],
                    "embedded_text": "Test product",
                }
            ],
        )
        connection.execute(
            insert(product_images),
            [
                {
                    "image_asset_key": "product-1-main",
                    "canonical_product_key": "product-1",
                    "product_id": "1001",
                    "image_rank": 1,
                    "is_og_image": True,
                    "image_role": "main",
                    "storage_backend_kind": REMOTE_IMAGE_STORAGE_BACKEND,
                    "storage_locator": "s3://bucket/product-1-main.jpg",
                    "public_url": public_url,
                    "canonical_image_url": "https://example.com/product-1-main.jpg",
                    "provenance": "test",
                }
            ],
        )
