"""Local toolset for search agent."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime
from logging import getLogger
from uuid import uuid4

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.shared import (
    build_room_3d_snapshot_context_payload,
    room_3d_repository,
    search_repository,
    telemetry_context,
)
from ikea_agent.chat.search_pipeline import run_search_pipeline_batch
from ikea_agent.persistence.room_3d_repository import Room3DSnapshotEntry
from ikea_agent.shared.types import (
    BundleProposalItemInput,
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
    SearchBatchToolResult,
    SearchQueryInput,
)

logger = getLogger(__name__)

TOOL_NAMES: tuple[str, ...] = (
    "run_search_graph",
    "propose_bundle",
    "list_room_3d_snapshot_context",
)


def _normalize_candidate_pool_limit(query: SearchQueryInput) -> int | None:
    if query.candidate_pool_limit is None:
        return None
    return max(query.limit, min(500, query.candidate_pool_limit))


def _normalize_search_queries(queries: list[SearchQueryInput]) -> list[SearchQueryInput]:
    if not queries:
        raise ValueError("Search batch must include at least one query.")
    return [
        replace(query, candidate_pool_limit=_normalize_candidate_pool_limit(query))
        for query in queries
    ]


async def run_search_graph(
    ctx: RunContext[SearchAgentDeps],
    queries: list[SearchQueryInput],
) -> SearchBatchToolResult:
    """Run one or more semantic searches in one batched embedding pass."""

    normalized_queries = _normalize_search_queries(queries)
    output = await run_search_pipeline_batch(
        runtime=ctx.deps.runtime,
        queries=normalized_queries,
    )
    logger.info(
        "search_batch_completed",
        extra={
            "query_count": len(output.queries),
            "returned_result_count": sum(query.returned_count for query in output.queries),
            **telemetry_context(ctx.deps.state),
        },
    )
    search_repo = search_repository(ctx.deps.runtime)
    if search_repo is not None:
        for query_input, query_output in zip(normalized_queries, output.queries, strict=True):
            search_repo.record_search_run(
                thread_id=ctx.deps.state.thread_id or "anonymous-thread",
                run_id=ctx.deps.state.run_id,
                query_text=query_input.semantic_query,
                filters=query_input.filters,
                warning=query_output.warning,
                total_candidates=query_output.total_candidates,
                results=query_output.results,
            )
    return output


def _hydrate_bundle_items(
    ctx: RunContext[SearchAgentDeps],
    items: list[BundleProposalItemInput],
) -> tuple[list[BundleProposalLineItem], float | None]:
    hydrated_items: list[BundleProposalLineItem] = []
    running_total = 0.0
    has_missing_price = False

    for item in items:
        if item.quantity < 1:
            raise ValueError(f"Bundle quantity for `{item.item_id}` must be at least 1.")
        product = ctx.deps.runtime.catalog_repository.read_product_by_key(product_key=item.item_id)
        if product is None:
            raise ValueError(f"Unknown product id `{item.item_id}`.")

        line_total = product.price_eur * item.quantity if product.price_eur is not None else None
        if line_total is None:
            has_missing_price = True
        else:
            running_total += line_total

        hydrated_items.append(
            BundleProposalLineItem(
                item_id=item.item_id,
                product_name=product.product_name,
                description_text=product.description_text,
                price_eur=product.price_eur,
                quantity=item.quantity,
                line_total_eur=line_total,
                reason=item.reason,
            )
        )

    return hydrated_items, None if has_missing_price else running_total


def _build_budget_validations(
    *,
    bundle_total: float | None,
    budget_cap_eur: float | None,
) -> list[BundleValidationResult]:
    if budget_cap_eur is None:
        return []
    if bundle_total is None:
        return [
            BundleValidationResult(
                kind="budget_max_eur",
                status="unknown",
                message=(
                    "Budget could not be checked because one or more items are missing prices."
                ),
            )
        ]
    if bundle_total <= budget_cap_eur:
        return [
            BundleValidationResult(
                kind="budget_max_eur",
                status="pass",
                message=(
                    f"Bundle total €{bundle_total:.2f} is within budget cap €{budget_cap_eur:.2f}."
                ),
            )
        ]
    return [
        BundleValidationResult(
            kind="budget_max_eur",
            status="fail",
            message=(f"Bundle total €{bundle_total:.2f} exceeds budget cap €{budget_cap_eur:.2f}."),
        )
    ]


def propose_bundle(
    ctx: RunContext[SearchAgentDeps],
    title: str,
    items: list[BundleProposalItemInput],
    notes: str | None = None,
    budget_cap_eur: float | None = None,
) -> BundleProposalToolResult:
    """Hydrate and append one optional bundle proposal for search UI rendering."""

    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Bundle title must not be blank.")
    if not items:
        raise ValueError("Bundle proposal must include at least one item.")

    hydrated_items, bundle_total = _hydrate_bundle_items(ctx, items)
    validations = _build_budget_validations(
        bundle_total=bundle_total,
        budget_cap_eur=budget_cap_eur,
    )
    result = BundleProposalToolResult(
        bundle_id=f"bundle-{uuid4().hex[:12]}",
        title=normalized_title,
        notes=notes.strip() if notes else None,
        budget_cap_eur=budget_cap_eur,
        items=hydrated_items,
        bundle_total_eur=bundle_total,
        validations=validations,
        created_at=datetime.now(UTC).isoformat(),
        run_id=ctx.deps.state.run_id,
    )
    ctx.deps.state.bundle_proposals.append(asdict(result))
    logger.info(
        "bundle_proposed",
        extra={
            "bundle_id": result.bundle_id,
            "bundle_item_count": len(result.items),
            **telemetry_context(ctx.deps.state),
        },
    )
    return result


def list_room_3d_snapshot_context(ctx: RunContext[SearchAgentDeps]) -> dict[str, object]:
    """Return captured 3D snapshot context from state and persisted thread records."""

    persisted: list[Room3DSnapshotEntry] = []
    repository = room_3d_repository(ctx.deps.runtime)
    if repository is not None and ctx.deps.state.thread_id is not None:
        persisted = repository.list_room_3d_snapshots(thread_id=ctx.deps.state.thread_id)
    payload = build_room_3d_snapshot_context_payload(
        state_snapshots=ctx.deps.state.room_3d_snapshots,
        persisted_snapshots=persisted,
    )
    logger.info(
        "list_room_3d_snapshot_context",
        extra={
            "state_snapshot_count": payload["state_count"],
            "persisted_snapshot_count": payload["persisted_count"],
            **telemetry_context(ctx.deps.state),
        },
    )
    return payload


def build_search_toolset() -> FunctionToolset[SearchAgentDeps]:
    """Build toolset for search agent."""

    return FunctionToolset(
        tools=[
            Tool(run_search_graph, name="run_search_graph"),
            Tool(propose_bundle, name="propose_bundle"),
            Tool(list_room_3d_snapshot_context, name="list_room_3d_snapshot_context"),
        ]
    )
