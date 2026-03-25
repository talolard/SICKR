"""Shared deploy-time readiness checks for seeded catalog state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, func, select

from ikea_agent.retrieval.schema import product_embeddings, product_images, products_canonical


@dataclass(frozen=True, slots=True)
class SeededCatalogReadiness:
    """Compact summary of whether seeded catalog data is usable for traffic."""

    status: Literal["ok", "failed"]
    detail: str
    products_count: int
    embeddings_count: int
    image_count: int
    missing_public_url_count: int
    image_serving_strategy: Literal["backend_proxy", "direct_public_url"]


def evaluate_seeded_catalog_readiness(
    engine: Engine,
    *,
    image_serving_strategy: Literal["backend_proxy", "direct_public_url"],
) -> SeededCatalogReadiness:
    """Verify that the required seeded catalog tables are populated for runtime use."""

    with engine.connect() as connection:
        products_count = int(
            connection.execute(select(func.count()).select_from(products_canonical)).scalar_one()
        )
        embeddings_count = int(
            connection.execute(select(func.count()).select_from(product_embeddings)).scalar_one()
        )
        image_count = int(
            connection.execute(select(func.count()).select_from(product_images)).scalar_one()
        )
        missing_public_url_count = int(
            connection.execute(
                select(func.count())
                .select_from(product_images)
                .where(
                    product_images.c.public_url.is_(None)
                    | (func.trim(product_images.c.public_url) == "")
                )
            ).scalar_one()
        )

    missing_datasets: list[str] = []
    if products_count <= 0:
        missing_datasets.append("catalog.products_canonical")
    if embeddings_count <= 0:
        missing_datasets.append("catalog.product_embeddings")
    if image_count <= 0:
        missing_datasets.append("catalog.product_images")
    if missing_datasets:
        return SeededCatalogReadiness(
            status="failed",
            detail=f"Required seeded catalog tables are empty: {', '.join(missing_datasets)}.",
            products_count=products_count,
            embeddings_count=embeddings_count,
            image_count=image_count,
            missing_public_url_count=missing_public_url_count,
            image_serving_strategy=image_serving_strategy,
        )

    if image_serving_strategy == "direct_public_url" and missing_public_url_count > 0:
        return SeededCatalogReadiness(
            status="failed",
            detail=(
                "Product image metadata is not ready for direct_public_url mode: "
                f"{missing_public_url_count} row(s) are missing public_url."
            ),
            products_count=products_count,
            embeddings_count=embeddings_count,
            image_count=image_count,
            missing_public_url_count=missing_public_url_count,
            image_serving_strategy=image_serving_strategy,
        )

    return SeededCatalogReadiness(
        status="ok",
        detail=(
            "Required seeded catalog tables are populated"
            if image_serving_strategy == "backend_proxy"
            else "Required seeded catalog tables are populated and public image URLs are ready."
        ),
        products_count=products_count,
        embeddings_count=embeddings_count,
        image_count=image_count,
        missing_public_url_count=missing_public_url_count,
        image_serving_strategy=image_serving_strategy,
    )
