from __future__ import annotations

from pathlib import Path

import duckdb

from tal_maria_ikea.retrieval.repository import RetrievalRepository, ShortlistRepository
from tal_maria_ikea.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
)

VECTOR_DIMENSIONS = 256


def _setup_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(Path("sql/10_schema.sql").read_text(encoding="utf-8"))
    connection.execute(Path("sql/14_market_views.sql").read_text(encoding="utf-8"))
    connection.execute(Path("sql/22_embedding_store.sql").read_text(encoding="utf-8"))


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
                list_resize([1.0, 0.0]::FLOAT[], 256, 0.0)::FLOAT[256], 'desk one', now()
            ),
            (
                '2-DE', 'gemini-embedding-001', 'run-1',
                list_resize([0.0, 1.0]::FLOAT[], 256, 0.0)::FLOAT[256], 'desk two', now()
            )
        """
    )


def test_retrieval_repository_search_filters_by_price_and_dimensions() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    _seed_products(connection)

    repository = RetrievalRepository(connection, vector_dimensions=VECTOR_DIMENSIONS)
    filters = RetrievalFilters(
        category="tables-desks",
        price=PriceFilterEUR(min_eur=90.0, max_eur=120.0),
        dimensions=DimensionFilter(width=DimensionAxisFilter(min_cm=110.0, max_cm=130.0)),
    )

    results = repository.search(
        query_vector=[1.0, 0.0],
        embedding_model="gemini-embedding-001",
        filters=filters,
        result_limit=10,
    )

    assert len(results) == 1
    assert results[0].canonical_product_key == "1-DE"


def test_shortlist_repository_add_remove_list() -> None:
    connection = duckdb.connect(":memory:")
    _setup_schema(connection)
    _seed_products(connection)

    repository = ShortlistRepository(connection)
    repository.add("1-DE", note="candidate")

    items = repository.list_items()
    assert len(items) == 1
    assert items[0].canonical_product_key == "1-DE"
    assert items[0].note == "candidate"

    repository.remove("1-DE")
    assert repository.list_items() == []
