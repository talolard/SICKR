from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.dialects import postgresql

from ikea_agent.retrieval.catalog_repository import (
    CatalogRepository,
    _build_postgres_neighbor_similarity_statement,
    _build_postgres_search_statement,
)
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine
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
        connection.exec_driver_sql(
            """
            INSERT INTO catalog.products_canonical (
                canonical_product_key,
                product_id,
                unique_id,
                country,
                product_name,
                display_title,
                product_type,
                description_text,
                main_category,
                sub_category,
                dimensions_text,
                width_cm,
                depth_cm,
                height_cm,
                price_eur,
                currency,
                rating,
                rating_count,
                badge,
                online_sellable,
                url,
                source_updated_at
            ) VALUES
                (
                    '1-DE', 1, '1-Germany', 'Germany', 'Desk One',
                    'Desk One Compact Workstation', 'Desk', 'Work desk',
                    'tables-desks', 'desks', '120x60x75 cm', 120, 60, 75, 100, 'EUR',
                    4.0, 10, 'none', true, 'https://example.com/1', now()
                ),
                (
                    '2-DE', 2, '2-Germany', 'Germany', 'Desk Two', null, 'Desk', 'Compact desk',
                    'tables-desks', 'desks', '100x50x74 cm', 100, 50, 74, 80, 'EUR',
                    4.5, 20, 'none', true, 'https://example.com/2', now()
                )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO catalog.product_embeddings (
                canonical_product_key,
                embedding_model,
                run_id,
                embedding_vector,
                embedded_text,
                embedded_at
            ) VALUES
                (
                    '1-DE', 'gemini-embedding-001', 'run-1',
                    [1.0, 0.0], 'line1\\nline2', now()
                ),
                (
                    '2-DE', 'gemini-embedding-001', 'run-1',
                    [0.0, 1.0], 'desk two', now()
                )
            """
        )


def test_hydrate_candidates_filters_by_price_and_dimensions(tmp_path: Path) -> None:
    engine = create_duckdb_engine(str(tmp_path / "retrieval_test_1.duckdb"))
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
    engine = create_duckdb_engine(str(tmp_path / "retrieval_test_2.duckdb"))
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
    engine = create_duckdb_engine(str(tmp_path / "retrieval_test_3.duckdb"))
    _setup_schema(engine)
    _seed_products(engine)

    repository = CatalogRepository(engine)

    product = repository.read_product_by_key(product_key="1-DE")

    assert product is not None
    assert product.product_name == "Desk One"
    assert product.display_title == "Desk One Compact Workstation"


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
