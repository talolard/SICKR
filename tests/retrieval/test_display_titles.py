from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

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


def test_derive_display_title_returns_empty_string_when_product_name_missing() -> None:
    assert (
        derive_display_title(
            product_name="   ",
            description_text="Anything",
            url="https://www.ikea.com/de/de/p/anything-123/",
        )
        == ""
    )


def test_derive_display_title_falls_back_to_base_name_when_slug_and_description_match() -> None:
    assert (
        derive_display_title(
            product_name="BESTA",
            description_text="BESTA",
            url="https://www.ikea.com/de/de/p/besta-19284756/",
        )
        == "BESTA"
    )


def test_derive_display_title_prefixes_family_name_for_description_only_variants() -> None:
    assert (
        derive_display_title(
            product_name="FEJKA",
            description_text="Artificial bamboo plant",
            url=None,
        )
        == "FEJKA Artificial bamboo plant"
    )


def test_derive_display_title_uses_description_directly_for_non_family_names() -> None:
    assert (
        derive_display_title(
            product_name="KALLAX Shelf Unit",
            description_text="White shelving unit with inserts",
            url=None,
        )
        == "White shelving unit with inserts"
    )


def test_derive_display_title_ignores_non_product_urls() -> None:
    assert (
        derive_display_title(
            product_name="MALM",
            description_text=None,
            url=str(urlparse("https://www.ikea.com/de/de/cat/storage-furniture-st001/").geturl()),
        )
        == "MALM"
    )


def test_backfill_product_display_titles_updates_catalog_rows_and_runtime_reads() -> None:
    engine = create_duckdb_engine(str(Path(".tmp_untracked/test_display_titles.duckdb")))
    ensure_runtime_schema(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM catalog.products_canonical")
        connection.exec_driver_sql(
            """
            INSERT INTO catalog.products_canonical (
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


def test_backfill_product_display_titles_skips_rows_with_existing_titles() -> None:
    engine = create_duckdb_engine(str(Path(".tmp_untracked/test_display_titles_existing.duckdb")))
    ensure_runtime_schema(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM catalog.products_canonical")
        connection.exec_driver_sql(
            """
            INSERT INTO catalog.products_canonical (
                canonical_product_key,
                product_id,
                unique_id,
                country,
                product_name,
                description_text,
                url,
                display_title,
                source_updated_at
            ) VALUES (
                'besta-1-DE',
                1,
                'besta-1-Germany',
                'Germany',
                'BESTA',
                'Storage combination',
                'https://www.ikea.com/de/de/p/besta-storage-combination-12345678/',
                'Custom title',
                now()
            )
            """
        )

    assert backfill_product_display_titles(engine) == 0
