from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ikea_agent.persistence.models import (
    SearchResultRecord,
    SearchRunRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.shared.sqlalchemy_db import create_duckdb_engine
from ikea_agent.shared.types import (
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
    SearchResultDiversityWarning,
    ShortRetrievalResult,
)


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_duckdb_engine(str(tmp_path / "search_repository_test.duckdb"))
    ensure_persistence_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_record_search_run_persists_filters_warning_and_ranked_results(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = SearchRepository(session_factory)

    search_id = repository.record_search_run(
        thread_id="thread-search",
        run_id=None,
        query_text="narrow wardrobe for hallway",
        filters=RetrievalFilters(
            category="Storage",
            include_keyword="wardrobe",
            sort="price_asc",
            price=PriceFilterEUR(min_eur=50.0, max_eur=400.0),
            dimensions=DimensionFilter(width=DimensionAxisFilter(max_cm=80.0)),
        ),
        warning=SearchResultDiversityWarning(
            kind="high_family_concentration",
            message="Results heavily concentrated in one family.",
            dominant_family="PAX",
            dominant_share=0.78,
            analyzed_result_count=20,
        ),
        total_candidates=36,
        results=[
            ShortRetrievalResult(
                product_id="prod-1",
                product_name="PAX Wardrobe 75",
                product_type="Wardrobe",
                description_text="Slim storage",
                main_category="Storage",
                sub_category="Wardrobes",
                width_cm=75.0,
                depth_cm=60.0,
                height_cm=236.0,
                price_eur=199.0,
            ),
            ShortRetrievalResult(
                product_id="prod-2",
                product_name="BRIMNES Wardrobe",
                product_type="Wardrobe",
                description_text="Narrow wardrobe",
                main_category="Storage",
                sub_category="Wardrobes",
                width_cm=78.0,
                depth_cm=50.0,
                height_cm=190.0,
                price_eur=149.0,
            ),
        ],
    )

    with session_factory() as session:
        run_row = session.execute(
            select(
                SearchRunRecord.thread_id,
                SearchRunRecord.query_text,
                SearchRunRecord.filters_json,
                SearchRunRecord.warning_json,
                SearchRunRecord.total_candidates,
                SearchRunRecord.returned_count,
            ).where(SearchRunRecord.search_id == search_id)
        ).one()
        result_rows = session.execute(
            select(
                SearchResultRecord.rank,
                SearchResultRecord.product_id,
                SearchResultRecord.product_name,
            )
            .where(SearchResultRecord.search_id == search_id)
            .order_by(SearchResultRecord.rank.asc())
        ).all()

    parsed_filters = json.loads(run_row.filters_json)
    parsed_warning = json.loads(run_row.warning_json)

    assert run_row.thread_id == "thread-search"
    assert run_row.query_text == "narrow wardrobe for hallway"
    assert run_row.total_candidates == 36
    assert run_row.returned_count == 2
    assert parsed_filters["category"] == "Storage"
    assert parsed_filters["price"]["min_eur"] == 50.0
    assert parsed_warning["dominant_family"] == "PAX"
    assert [item.rank for item in result_rows] == [1, 2]
    assert [item.product_id for item in result_rows] == ["prod-1", "prod-2"]


def test_list_search_runs_returns_newest_first(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = SearchRepository(session_factory)

    first_id = repository.record_search_run(
        thread_id="thread-search-order",
        run_id=None,
        query_text="desk lamp",
        filters=None,
        warning=None,
        total_candidates=5,
        results=[],
    )
    second_id = repository.record_search_run(
        thread_id="thread-search-order",
        run_id=None,
        query_text="desk organizer",
        filters=RetrievalFilters(include_keyword="organizer"),
        warning=None,
        total_candidates=8,
        results=[],
    )

    ids = repository.list_search_runs(thread_id="thread-search-order")

    assert ids[0] == second_id
    assert ids[1] == first_id
