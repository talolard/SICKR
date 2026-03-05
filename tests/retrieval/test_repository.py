from __future__ import annotations

import duckdb

from ikea_agent.retrieval.catalog_repository import CatalogRepository
from ikea_agent.retrieval.service import VectorMatch
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
)


def _setup_schema(connection: duckdb.DuckDBPyConnection) -> None:
    ensure_runtime_schema(connection)


def _seed_products(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        INSERT INTO app.products_canonical (
            canonical_product_key,
            product_id,
            unique_id,
            country,
            product_name,
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
                '1-DE', 1, '1-Germany', 'Germany', 'Desk One', 'Desk', 'Work desk',
                'tables-desks', 'desks', '120x60x75 cm', 120, 60, 75, 100, 'EUR',
                4.0, 10, 'none', true, 'https://example.com/1', now()
            ),
            (
                '2-DE', 2, '2-Germany', 'Germany', 'Desk Two', 'Desk', 'Compact desk',
                'tables-desks', 'desks', '100x50x74 cm', 100, 50, 74, 80, 'EUR',
                4.5, 20, 'none', true, 'https://example.com/2', now()
            )
        """
    )
    connection.execute(
        """
        INSERT INTO app.product_embeddings (
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


def test_hydrate_candidates_filters_by_price_and_dimensions() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    _seed_products(connection)

    repository = CatalogRepository(connection)
    filters = RetrievalFilters(
        category="tables-desks",
        price=PriceFilterEUR(min_eur=90.0, max_eur=120.0),
        dimensions=DimensionFilter(width=DimensionAxisFilter(min_cm=110.0, max_cm=130.0)),
    )

    results = repository.hydrate_candidates(
        candidates=[
            VectorMatch(canonical_product_key="1-DE", semantic_score=0.95),
            VectorMatch(canonical_product_key="2-DE", semantic_score=0.85),
        ],
        filters=filters,
        result_limit=10,
    )

    assert len(results) == 1
    assert results[0].canonical_product_key == "1-DE"
    assert results[0].embedding_text == "line1\nline2"


def test_hydrate_candidates_filters_by_include_and_exclude_keyword() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    _seed_products(connection)

    repository = CatalogRepository(connection)
    filters = RetrievalFilters(
        include_keyword="work",
        exclude_keyword="compact",
    )

    results = repository.hydrate_candidates(
        candidates=[
            VectorMatch(canonical_product_key="1-DE", semantic_score=0.9),
            VectorMatch(canonical_product_key="2-DE", semantic_score=0.8),
        ],
        filters=filters,
        result_limit=10,
    )

    assert len(results) == 1
    assert results[0].canonical_product_key == "1-DE"
