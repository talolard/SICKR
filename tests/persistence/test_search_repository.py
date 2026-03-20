from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.shared.sqlite_db import create_sqlite_engine

from ikea_agent.persistence.models import (
    BundleProposalRecord,
    SearchResultRecord,
    SearchRunRecord,
    ensure_persistence_schema,
)
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.shared.types import (
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
    DimensionAxisFilter,
    DimensionFilter,
    PriceFilterEUR,
    RetrievalFilters,
    SearchResultDiversityWarning,
    ShortRetrievalResult,
)


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_sqlite_engine(tmp_path / "search_repository_test.sqlite")
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


def test_record_bundle_proposal_persists_and_lists_typed_payloads(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = SearchRepository(session_factory)

    bundle_id = repository.record_bundle_proposal(
        thread_id="thread-search-order",
        run_id=None,
        proposal=BundleProposalToolResult(
            bundle_id="bundle-1",
            title="Desk starter bundle",
            notes="Fits a compact office.",
            budget_cap_eur=200.0,
            items=[
                BundleProposalLineItem(
                    item_id="chair-1",
                    product_name="Chair One",
                    product_url="https://www.ikea.com/de/de/p/chair-one-12345678/",
                    description_text="Desk chair",
                    price_eur=79.99,
                    quantity=2,
                    line_total_eur=159.98,
                    reason="Matched seating",
                )
            ],
            bundle_total_eur=159.98,
            validations=[
                BundleValidationResult(
                    kind="pricing_complete",
                    status="pass",
                    message="All bundle items have prices, so the total is complete.",
                ),
                BundleValidationResult(
                    kind="budget_max_eur",
                    status="pass",
                    message="Bundle total €159.98 is within budget cap €200.00.",
                ),
            ],
            created_at="2026-03-11T11:00:00+00:00",
            run_id=None,
        ),
    )

    with session_factory() as session:
        row = session.execute(
            select(
                BundleProposalRecord.thread_id,
                BundleProposalRecord.title,
                BundleProposalRecord.items_json,
                BundleProposalRecord.validations_json,
            ).where(BundleProposalRecord.bundle_id == bundle_id)
        ).one()

    listed = repository.list_bundle_proposals(thread_id="thread-search-order")
    parsed_items = json.loads(row.items_json)
    parsed_validations = json.loads(row.validations_json)

    assert row.thread_id == "thread-search-order"
    assert row.title == "Desk starter bundle"
    assert parsed_items[0]["item_id"] == "chair-1"
    assert parsed_items[0]["product_url"] == "https://www.ikea.com/de/de/p/chair-one-12345678/"
    assert parsed_validations[1]["kind"] == "budget_max_eur"
    assert listed[0].bundle_id == "bundle-1"
    assert listed[0].items[0].line_total_eur == 159.98
    assert listed[0].items[0].image_urls == []
    assert listed[0].items[0].product_url == "https://www.ikea.com/de/de/p/chair-one-12345678/"


def test_record_bundle_proposal_persists_and_lists_newest_first(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    repository = SearchRepository(session_factory)

    first = BundleProposalToolResult(
        bundle_id="bundle-1",
        title="Desk setup",
        notes="Starter bundle",
        budget_cap_eur=300.0,
        items=[
            BundleProposalLineItem(
                item_id="chair-1",
                product_name="Desk chair",
                product_url="https://www.ikea.com/de/de/p/chair-one-12345678/",
                description_text="Supportive chair",
                price_eur=99.0,
                quantity=1,
                line_total_eur=99.0,
                reason="Primary seating",
            )
        ],
        bundle_total_eur=99.0,
        validations=[
            BundleValidationResult(
                kind="pricing_complete",
                status="pass",
                message="All bundle items have prices, so the total is complete.",
            )
        ],
        created_at="2026-03-11T10:00:00+00:00",
        run_id=None,
    )
    second = BundleProposalToolResult(
        bundle_id="bundle-2",
        title="Desk setup v2",
        notes=None,
        budget_cap_eur=350.0,
        items=[
            BundleProposalLineItem(
                item_id="chair-2",
                product_name="Guest chair",
                product_url="https://www.ikea.com/de/de/p/chair-two-87654321/",
                description_text=None,
                price_eur=49.0,
                quantity=2,
                line_total_eur=98.0,
                reason="Guest seating",
            )
        ],
        bundle_total_eur=98.0,
        validations=[
            BundleValidationResult(
                kind="duplicate_items",
                status="warn",
                message="Merged 1 repeated product entry into combined quantities.",
            )
        ],
        created_at="2026-03-11T11:00:00+00:00",
        run_id=None,
    )

    repository.record_bundle_proposal(thread_id="thread-search", run_id=None, proposal=first)
    repository.record_bundle_proposal(thread_id="thread-search", run_id=None, proposal=second)

    listed = repository.list_bundle_proposals(thread_id="thread-search")

    assert [item.bundle_id for item in listed] == ["bundle-2", "bundle-1"]
    assert listed[0].validations[0].kind == "duplicate_items"

    with session_factory() as session:
        count = session.execute(select(BundleProposalRecord.bundle_id)).all()

    assert len(count) == 2
