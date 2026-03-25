from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.dialects import postgresql
from tests.shared.runtime_schema import ensure_runtime_schema
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.retrieval.catalog_repository import (
    CatalogRepository,
    _build_postgres_neighbor_similarity_statement,
    _build_postgres_search_statement,
)
from ikea_agent.retrieval.schema import product_embeddings, product_images, products_canonical
from ikea_agent.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
)


def _setup_schema(engine: Engine) -> None:
    ensure_runtime_schema(engine)


def _seed_products(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            products_canonical.insert(),
            [
                {
                    "canonical_product_key": "1-DE",
                    "product_id": 1,
                    "unique_id": "1-Germany",
                    "country": "Germany",
                    "product_name": "Desk One",
                    "display_title": "Desk One Compact Workstation",
                    "product_type": "Desk",
                    "description_text": "Work desk",
                    "main_category": "tables-desks",
                    "sub_category": "desks",
                    "dimensions_text": "120x60x75 cm",
                    "width_cm": 120.0,
                    "depth_cm": 60.0,
                    "height_cm": 75.0,
                    "price_eur": 100.0,
                    "currency": "EUR",
                    "rating": 4.0,
                    "rating_count": 10,
                    "badge": "none",
                    "online_sellable": True,
                    "url": "https://example.com/1",
                    "source_updated_at": datetime.now(UTC),
                },
                {
                    "canonical_product_key": "2-DE",
                    "product_id": 2,
                    "unique_id": "2-Germany",
                    "country": "Germany",
                    "product_name": "Desk Two",
                    "display_title": None,
                    "product_type": "Desk",
                    "description_text": "Compact desk",
                    "main_category": "tables-desks",
                    "sub_category": "desks",
                    "dimensions_text": "100x50x74 cm",
                    "width_cm": 100.0,
                    "depth_cm": 50.0,
                    "height_cm": 74.0,
                    "price_eur": 80.0,
                    "currency": "EUR",
                    "rating": 4.5,
                    "rating_count": 20,
                    "badge": "none",
                    "online_sellable": True,
                    "url": "https://example.com/2",
                    "source_updated_at": datetime.now(UTC),
                },
            ],
        )
        connection.execute(
            product_embeddings.insert(),
            [
                {
                    "canonical_product_key": "1-DE",
                    "embedding_model": "gemini-embedding-001",
                    "run_id": "run-1",
                    "embedding_vector": [1.0, 0.0],
                    "embedded_text": "line1\\nline2",
                    "embedded_at": datetime.now(UTC),
                },
                {
                    "canonical_product_key": "2-DE",
                    "embedding_model": "gemini-embedding-001",
                    "run_id": "run-1",
                    "embedding_vector": [0.0, 1.0],
                    "embedded_text": "desk two",
                    "embedded_at": datetime.now(UTC),
                },
            ],
        )
        connection.execute(
            product_images.insert(),
            [
                {
                    "image_asset_key": "1-primary.jpg",
                    "canonical_product_key": "1-DE",
                    "product_id": "1",
                    "image_rank": 5,
                    "is_og_image": True,
                    "storage_backend_kind": "local_shared_root",
                    "storage_locator": "catalog/1-primary.jpg",
                    "public_url": "https://example.com/images/1-primary.jpg",
                    "local_path": None,
                },
                {
                    "image_asset_key": "1-detail.jpg",
                    "canonical_product_key": "1-DE",
                    "product_id": "1",
                    "image_rank": 2,
                    "is_og_image": False,
                    "storage_backend_kind": "local_shared_root",
                    "storage_locator": "catalog/1-detail.jpg",
                    "public_url": "https://example.com/images/1-detail.jpg",
                    "local_path": None,
                },
            ],
        )


def test_hydrate_candidates_filters_by_price_and_dimensions(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "retrieval_test_1.sqlite")
    _setup_schema(engine)
    _seed_products(engine)

    repository = CatalogRepository(engine)
    filters = RetrievalFilters(
        category="tables-desks",
        price=PriceFilterEUR(min_eur=90.0, max_eur=120.0),
        dimensions=DimensionFilter(width=DimensionAxisFilter(min_cm=110.0, max_cm=130.0)),
    )

    results = repository.search_semantic_products(
        query_vector=(1.0, 0.0),
        embedding_model="gemini-embedding-001",
        filters=filters,
        result_limit=10,
    )

    assert len(results) == 1
    assert results[0].canonical_product_key == "1-DE"
    assert results[0].embedding_text == "line1\nline2"
    assert results[0].display_title == "Desk One Compact Workstation"


def test_hydrate_candidates_filters_by_include_and_exclude_keyword(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "retrieval_test_2.sqlite")
    _setup_schema(engine)
    _seed_products(engine)

    repository = CatalogRepository(engine)
    filters = RetrievalFilters(
        include_keyword="work",
        exclude_keyword="compact",
    )

    results = repository.search_semantic_products(
        query_vector=(1.0, 0.0),
        embedding_model="gemini-embedding-001",
        filters=filters,
        result_limit=10,
    )

    assert len(results) == 1
    assert results[0].canonical_product_key == "1-DE"
    assert results[0].rank_explanation == "legacy cosine score 1.000"


def test_read_product_by_key_preserves_family_name_and_exposes_display_title(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "retrieval_test_3.sqlite")
    _setup_schema(engine)
    _seed_products(engine)

    repository = CatalogRepository(engine)

    product = repository.read_product_by_key(product_key="1-DE")

    assert product is not None
    assert product.product_name == "Desk One"
    assert product.display_title == "Desk One Compact Workstation"


def test_read_image_urls_by_product_keys_returns_ordered_proxy_urls(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "retrieval_test_4.sqlite")
    _setup_schema(engine)
    _seed_products(engine)

    repository = CatalogRepository(engine)

    image_urls = repository.read_image_urls_by_product_keys(
        canonical_product_keys=["1-DE"],
        serving_strategy="backend_proxy",
        base_url=None,
    )

    assert image_urls == {
        "1-DE": (
            "/static/product-images/1",
            "/static/product-images/1/2",
        )
    }


def test_read_image_urls_by_product_keys_rejects_missing_seeded_public_urls(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "retrieval_test_4b.sqlite")
    _setup_schema(engine)
    _seed_products(engine)
    with engine.begin() as connection:
        connection.execute(
            product_images.update()
            .where(product_images.c.canonical_product_key == "1-DE")
            .values(public_url=None, crawl_run_id="catalog-run-9")
        )

    repository = CatalogRepository(engine)

    with pytest.raises(
        ValueError,
        match=r"requires seeded catalog\.product_images\.public_url",
    ):
        repository.read_image_urls_by_product_keys(
            canonical_product_keys=["1-DE"],
            serving_strategy="direct_public_url",
            base_url="https://designagent.talperry.com/static/product-images",
        )


def test_resolve_product_image_path_returns_ranked_local_path(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "retrieval_test_5.sqlite")
    _setup_schema(engine)
    _seed_products(engine)
    image_root = tmp_path / "images"
    image_root.mkdir()
    primary_path = image_root / "primary.jpg"
    detail_path = image_root / "detail.jpg"
    primary_path.write_bytes(b"primary")
    detail_path.write_bytes(b"detail")
    with engine.begin() as connection:
        connection.execute(product_images.delete())
        connection.execute(
            product_images.insert(),
            [
                {
                    "image_asset_key": "1-primary-local.jpg",
                    "canonical_product_key": "1-DE",
                    "product_id": "1",
                    "image_rank": 5,
                    "is_og_image": True,
                    "storage_backend_kind": "local_shared_root",
                    "storage_locator": str(primary_path),
                    "public_url": None,
                    "local_path": str(primary_path),
                },
                {
                    "image_asset_key": "1-detail-local.jpg",
                    "canonical_product_key": "1-DE",
                    "product_id": "1",
                    "image_rank": 2,
                    "is_og_image": False,
                    "storage_backend_kind": "local_shared_root",
                    "storage_locator": str(detail_path),
                    "public_url": None,
                    "local_path": str(detail_path),
                },
            ],
        )

    repository = CatalogRepository(engine)

    assert repository.resolve_product_image_path(product_id="1") == primary_path.resolve()
    assert repository.resolve_product_image_path(product_id="1", ordinal=2) == detail_path.resolve()


def test_postgres_search_statement_uses_pgvector_distance_and_sqlalchemy_filters() -> None:
    filters = RetrievalFilters(
        category="tables-desks",
        include_keyword="work",
        exclude_keyword="compact",
        price=PriceFilterEUR(min_eur=90.0, max_eur=120.0),
        dimensions=DimensionFilter(width=DimensionAxisFilter(min_cm=110.0, max_cm=130.0)),
    )

    compiled = str(_build_postgres_search_statement(filters).compile(dialect=postgresql.dialect()))

    assert "catalog.product_embeddings.embedding_vector <=> %(query_vector)s" in compiled
    assert "JOIN catalog.products_canonical" in compiled
    assert "catalog.products_canonical.main_category = %(category)s" in compiled
    assert "catalog.products_canonical.price_eur >= %(price_min_eur)s" in compiled
    assert "catalog.products_canonical.width_cm >= %(width_min_cm)s" in compiled
    assert "LIKE '%%' || %(include_keyword)s || '%%'" in compiled


def test_postgres_neighbor_similarity_statement_uses_pgvector_pair_distance() -> None:
    compiled = str(
        _build_postgres_neighbor_similarity_statement().compile(dialect=postgresql.dialect())
    )

    assert "source_embeddings.embedding_vector <=> neighbor_embeddings.embedding_vector" in compiled
    assert "source_embeddings.canonical_product_key IN (__[POSTCOMPILE_source_keys])" in compiled
    assert (
        "neighbor_embeddings.canonical_product_key IN (__[POSTCOMPILE_neighbor_keys])" in compiled
    )
