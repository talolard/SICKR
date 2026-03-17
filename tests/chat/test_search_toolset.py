from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import cast

import pytest
from pydantic_ai import RunContext

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.search.toolset import (
    SearchToolsetServices,
    build_search_toolset,
    propose_bundle,
)
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.shared.types import (
    BundleProposalItemInput,
    BundleProposalToolResult,
    RetrievalResult,
    SearchBatchToolResult,
    SearchQueryInput,
    SearchQueryToolResult,
    ShortRetrievalResult,
)

RunSearchGraphFunc = Callable[
    [RunContext[SearchAgentDeps], list[SearchQueryInput]],
    Awaitable[SearchBatchToolResult],
]
ProposeBundleFunc = Callable[
    [RunContext[SearchAgentDeps], str, list[BundleProposalItemInput], str | None, float | None],
    BundleProposalToolResult,
]


@dataclass(frozen=True, slots=True)
class _CatalogStub:
    price_eur: float | None

    def read_product_by_key(self, *, product_key: str) -> RetrievalResult | None:
        return RetrievalResult(
            canonical_product_key=product_key,
            product_name=f"Product {product_key}",
            product_type="Chair",
            description_text="Useful chair",
            embedding_text=None,
            main_category="chairs",
            sub_category="desk",
            dimensions_text="50x50x90",
            width_cm=50.0,
            depth_cm=50.0,
            height_cm=90.0,
            price_eur=self.price_eur,
            url=None,
            semantic_score=0.9,
            filter_pass_reasons=("ok",),
            rank_explanation="score",
        )


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    catalog_repository: _CatalogStub


@dataclass(slots=True)
class _SearchRepositorySpy:
    proposals: list[BundleProposalToolResult] = field(default_factory=list)

    def record_bundle_proposal(
        self,
        *,
        thread_id: str,
        run_id: str | None,
        proposal: BundleProposalToolResult,
    ) -> str:
        _ = (thread_id, run_id)
        self.proposals.append(proposal)
        return proposal.bundle_id


@dataclass(slots=True)
class _SearchPipelineSpy:
    calls: list[list[SearchQueryInput]] = field(default_factory=list)

    async def __call__(
        self,
        *,
        runtime: ChatRuntime,
        queries: list[SearchQueryInput],
    ) -> SearchBatchToolResult:
        _ = runtime
        self.calls.append(queries)
        return SearchBatchToolResult(
            queries=[
                SearchQueryToolResult(
                    query_id=query.query_id,
                    semantic_query=query.semantic_query,
                    results=[
                        ShortRetrievalResult(
                            product_id=f"{query.query_id}-1",
                            product_name=f"Result for {query.query_id}",
                            product_type="Chair",
                            description_text="Picked by tool test",
                            main_category="chairs",
                            sub_category="desk",
                            width_cm=50.0,
                            depth_cm=50.0,
                            height_cm=90.0,
                            price_eur=99.0,
                        )
                    ],
                    total_candidates=4,
                    returned_count=1,
                )
                for query in queries
            ]
        )


def _run_context(*, price_eur: float | None) -> RunContext[SearchAgentDeps]:
    deps = SearchAgentDeps(
        runtime=cast(
            "ChatRuntime", _RuntimeStub(catalog_repository=_CatalogStub(price_eur=price_eur))
        ),
        attachment_store=cast("AttachmentStore", object()),
        state=SearchAgentState(thread_id="thread-1", run_id="run-1"),
    )
    return cast("RunContext[SearchAgentDeps]", SimpleNamespace(deps=deps))


def _ground_item(ctx: RunContext[SearchAgentDeps], *, item_id: str) -> None:
    ctx.deps.state.remember_search_batch(
        SearchBatchToolResult(
            queries=[
                SearchQueryToolResult(
                    query_id="grounding-query",
                    semantic_query="grounding query",
                    results=[
                        ShortRetrievalResult(
                            product_id=item_id,
                            product_name=f"Grounded {item_id}",
                            product_type="Chair",
                            description_text="Grounded by test search",
                            main_category="chairs",
                            sub_category="desk",
                            width_cm=50.0,
                            depth_cm=50.0,
                            height_cm=90.0,
                            price_eur=99.0,
                        )
                    ],
                    total_candidates=1,
                    returned_count=1,
                )
            ]
        )
    )


def _services(
    *,
    pipeline: _SearchPipelineSpy,
    search_repository_override: _SearchRepositorySpy | None = None,
) -> SearchToolsetServices:
    return SearchToolsetServices(
        run_search_batch=pipeline,
        get_search_repository=lambda _runtime: cast(
            "SearchRepository | None",
            search_repository_override,
        ),
        get_room_3d_repository=lambda _runtime: None,
    )


async def _run_search_graph_once(
    run_search_graph: RunSearchGraphFunc,
    ctx: RunContext[SearchAgentDeps],
    queries: list[SearchQueryInput],
) -> SearchBatchToolResult:
    return await run_search_graph(ctx, queries)


def test_run_search_graph_forwards_one_batched_query_list() -> None:
    ctx = _run_context(price_eur=20.0)
    pipeline_spy = _SearchPipelineSpy()
    toolset = build_search_toolset(_services(pipeline=pipeline_spy))
    run_search_graph = cast("RunSearchGraphFunc", toolset.tools["run_search_graph"].function)

    result = asyncio.run(
        _run_search_graph_once(
            run_search_graph,
            ctx,
            [
                SearchQueryInput(query_id="desk", semantic_query="small desk"),
                SearchQueryInput(query_id="lamp", semantic_query="task lamp", limit=3),
            ],
        )
    )

    assert len(pipeline_spy.calls) == 1
    assert [query.query_id for query in pipeline_spy.calls[0]] == ["desk", "lamp"]
    assert [query.query_id for query in result.queries] == ["desk", "lamp"]
    assert [item.product_id for item in ctx.deps.state.grounded_products] == ["desk-1", "lamp-1"]


def test_propose_bundle_appends_typed_bundle_persists_and_reports_budget_failure() -> None:
    ctx = _run_context(price_eur=20.0)
    _ground_item(ctx, item_id="chair-1")
    pipeline_spy = _SearchPipelineSpy()
    repository_spy = _SearchRepositorySpy()
    toolset = build_search_toolset(
        _services(
            pipeline=pipeline_spy,
            search_repository_override=repository_spy,
        )
    )
    propose_bundle = cast("ProposeBundleFunc", toolset.tools["propose_bundle"].function)

    result = propose_bundle(
        ctx,
        "Desk seating bundle",
        [BundleProposalItemInput(item_id="chair-1", quantity=2, reason="Seat for desk work")],
        None,
        30.0,
    )

    assert result.title == "Desk seating bundle"
    assert result.bundle_total_eur == 40.0
    assert result.items[0].line_total_eur == 40.0
    assert [validation.kind for validation in result.validations] == [
        "pricing_complete",
        "duplicate_items",
        "budget_max_eur",
    ]
    assert result.validations[-1].status == "fail"
    assert ctx.deps.state.bundle_proposals[0].bundle_id == result.bundle_id
    assert repository_spy.proposals[0] == result


def test_propose_bundle_merges_duplicates_and_reports_warning() -> None:
    ctx = _run_context(price_eur=15.0)
    _ground_item(ctx, item_id="chair-1")

    result = propose_bundle(
        ctx,
        title="Desk seating bundle",
        items=[
            BundleProposalItemInput(item_id="chair-1", quantity=1, reason="Seat at desk"),
            BundleProposalItemInput(item_id="chair-1", quantity=2, reason="Guest seating"),
        ],
    )

    assert len(result.items) == 1
    assert result.items[0].quantity == 3
    assert result.bundle_total_eur == 45.0
    duplicate_validation = next(
        validation for validation in result.validations if validation.kind == "duplicate_items"
    )
    assert duplicate_validation.status == "warn"


def test_propose_bundle_reports_unknown_budget_when_prices_are_missing() -> None:
    ctx = _run_context(price_eur=None)
    _ground_item(ctx, item_id="chair-2")

    result = propose_bundle(
        ctx,
        title="Concept bundle",
        budget_cap_eur=100.0,
        notes="Needs pricing follow-up.",
        items=[BundleProposalItemInput(item_id="chair-2", quantity=1, reason="Placeholder item")],
    )

    assert result.bundle_total_eur is None
    pricing_validation = next(
        validation for validation in result.validations if validation.kind == "pricing_complete"
    )
    budget_validation = next(
        validation for validation in result.validations if validation.kind == "budget_max_eur"
    )
    assert pricing_validation.status == "warn"
    assert budget_validation.status == "unknown"
    assert result.notes == "Needs pricing follow-up."


def test_propose_bundle_rejects_items_that_were_not_grounded_by_search() -> None:
    ctx = _run_context(price_eur=20.0)
    _ground_item(ctx, item_id="chair-1")

    with pytest.raises(ValueError, match="Ungrounded item ids: `chair-2`"):
        propose_bundle(
            ctx,
            title="Desk seating bundle",
            items=[BundleProposalItemInput(item_id="chair-2", quantity=1, reason="Seat at desk")],
        )
