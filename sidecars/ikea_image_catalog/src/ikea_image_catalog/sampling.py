"""Input sampling from the repo's parquet product snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb

from ikea_image_catalog.extractors import build_page_fetch_url
from ikea_image_catalog.models import ProductSeed

RAW_PRODUCTS_GLOB = "data/parquet/products_raw/country=*/data_0.parquet"
CANONICAL_PRODUCTS_PATH = "data/parquet/products_canonical/country=Germany/data_0.parquet"


def load_product_seeds(
    *,
    repo_root: Path,
    limit: int,
    countries: Sequence[str] | None = None,
) -> list[ProductSeed]:
    """Read a deterministic sample of product-page inputs from repo parquet data."""

    if limit <= 0:
        msg = f"limit must be positive, got {limit}"
        raise ValueError(msg)

    raw_glob = str((repo_root / RAW_PRODUCTS_GLOB).resolve())
    canonical_path = (repo_root / CANONICAL_PRODUCTS_PATH).resolve()
    where_parts = ["url IS NOT NULL", "length(trim(url)) > 0"]
    if countries:
        quoted_countries = [country.replace("'", "''") for country in countries]
        quoted = ", ".join(f"'{country}'" for country in quoted_countries)
        where_parts.append(f"country IN ({quoted})")
    where_sql = " AND ".join(where_parts)
    query = f"""
        SELECT
            CAST(product_id AS VARCHAR) AS product_id,
            COALESCE(product_name, '') AS product_name,
            country,
            trim(url) AS source_page_url
        FROM read_parquet('{raw_glob}')
        WHERE {where_sql}
        ORDER BY md5(country || '|' || trim(url))
        LIMIT {limit}
    """

    product_key_lookup: dict[str, str] = {}
    if canonical_path.exists():
        for product_id, canonical_product_key in duckdb.sql(
            f"""
            SELECT DISTINCT
                CAST(product_id AS VARCHAR) AS product_id,
                canonical_product_key
            FROM read_parquet('{canonical_path}')
            WHERE canonical_product_key IS NOT NULL
            """
        ).fetchall():
            if product_id is None or canonical_product_key is None:
                continue
            product_key_lookup[str(product_id)] = str(canonical_product_key)

    rows = duckdb.sql(query).fetchall()
    return [
        ProductSeed(
            product_id=str(product_id),
            repo_canonical_product_key=product_key_lookup.get(str(product_id)),
            product_name=str(product_name),
            country=str(country),
            source_page_url=str(source_page_url),
            page_fetch_url=build_page_fetch_url(str(source_page_url)),
        )
        for product_id, product_name, country, source_page_url in rows
    ]
