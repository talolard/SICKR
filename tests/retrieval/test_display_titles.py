from __future__ import annotations

from pathlib import Path

from ikea_agent.retrieval.catalog_repository import CatalogRepository
from ikea_agent.retrieval.display_titles import (
    backfill_product_display_titles,
    derive_display_title,
)
from ikea_agent.shared.bootstrap import ensure_runtime_schema
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine


def test_derive_display_title_prefers_specific_slug_metadata() -> None:
    assert (
        derive_display_title(
            product_name="FEJKA",
            description_text="Artificial potted plant, indoor/outdoor monstera",
            url="https://www.ikea.com/de/de/p/fejka-kuenstliche-topfpflanze-drinnen-draussen-monstera-30582542/",
        )
        == "FEJKA Kuenstliche Topfpflanze Drinnen Draussen Monstera"
    )


def test_backfill_product_display_titles_updates_catalog_rows_and_runtime_reads() -> None:
    engine = create_duckdb_engine(str(Path(".tmp_untracked/test_display_titles.duckdb")))
    ensure_runtime_schema(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM app.products_canonical")
        connection.exec_driver_sql(
            """
            INSERT INTO app.products_canonical (
                canonical_product_key,
                product_id,
                unique_id,
                country,
                product_name,
                description_text,
                url,
                source_updated_at
            ) VALUES (
                'fejka-1-DE',
                1,
                'fejka-1-Germany',
                'Germany',
                'FEJKA',
                'Artificial potted plant, indoor/outdoor monstera',
                'https://www.ikea.com/de/de/p/fejka-kuenstliche-topfpflanze-drinnen-draussen-monstera-30582542/',
                now()
            )
            """
        )

    updated_count = backfill_product_display_titles(engine)

    repository = CatalogRepository(engine)
    product = repository.read_product_by_key(product_key="fejka-1-DE")

    assert updated_count == 1
    assert product is not None
    assert product.product_name == "FEJKA"
    assert product.display_title == "FEJKA Kuenstliche Topfpflanze Drinnen Draussen Monstera"
