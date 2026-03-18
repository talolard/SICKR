"""Local toolset for search agent."""

from __future__ import annotations

from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from logging import getLogger
from uuid import uuid4

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.shared import (
    build_remember_preference_tool,
    build_room_3d_snapshot_context_payload,
    room_3d_repository,
    search_repository,
    telemetry_context,
)
from ikea_agent.chat.product_images import image_urls_for_runtime
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat.search_pipeline import run_search_pipeline_batch
from ikea_agent.persistence.room_3d_repository import Room3DRepository, Room3DSnapshotEntry
from ikea_agent.persistence.search_repository import SearchRepository
from ikea_agent.shared.types import (
    BundleProposalItemInput,
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
    SearchBatchToolResult,
    SearchQueryInput,
    ToolFailureResult,
)

logger = getLogger(__name__)

TOOL_NAMES: tuple[str, ...] = (
    "remember_preference",
    "run_search_graph",
    "propose_bundle",
    "list_room_3d_snapshot_context",
)

SearchBatchRunner = Callable[..., Awaitable[SearchBatchToolResult]]
SearchRepositoryFactory = Callable[[ChatRuntime], SearchRepository | None]
Room3DRepositoryFactory = Callable[[ChatRuntime], Room3DRepository | None]


@dataclass(frozen=True, slots=True)
class SearchToolsetServices:
    """Service seams for search tools.

    Keeping these seams explicit lets evals and deterministic tests replace
    infrastructure-heavy operations without mutating module globals.
    """

    run_search_batch: SearchBatchRunner
    get_search_repository: SearchRepositoryFactory
    get_room_3d_repository: Room3DRepositoryFactory


def default_search_toolset_services() -> SearchToolsetServices:
    """Return the current default service bindings for the search toolset."""

    return SearchToolsetServices(
        run_search_batch=run_search_pipeline_batch,
        get_search_repository=search_repository,
        get_room_3d_repository=room_3d_repository,
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


async def _run_search_graph_with_services(
    ctx: RunContext[SearchAgentDeps],
    queries: list[SearchQueryInput],
    *,
    services: SearchToolsetServices,
) -> SearchBatchToolResult:
    normalized_queries = _normalize_search_queries(queries)
    output = await services.run_search_batch(
        runtime=ctx.deps.runtime,
        queries=normalized_queries,
    )
    ctx.deps.state.remember_search_batch(output)
    logger.info(
        "search_batch_completed",
        extra={
            "query_count": len(output.queries),
            "returned_result_count": sum(query.returned_count for query in output.queries),
            **telemetry_context(ctx.deps.state),
        },
    )
    search_repo = services.get_search_repository(ctx.deps.runtime)
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


async def run_search_graph(
    ctx: RunContext[SearchAgentDeps],
    queries: list[SearchQueryInput],
) -> SearchBatchToolResult:
    """Run one or more semantic searches in one batched embedding pass."""

    return await _run_search_graph_with_services(
        ctx,
        queries,
        services=default_search_toolset_services(),
    )


def _hydrate_bundle_items(
    ctx: RunContext[SearchAgentDeps],
    items: list[BundleProposalItemInput],
) -> tuple[list[BundleProposalLineItem], float | None, int]:
    hydrated_items: list[BundleProposalLineItem] = []
    running_total = 0.0
    missing_price_count = 0

    for item in items:
        product = ctx.deps.runtime.catalog_repository.read_product_by_key(product_key=item.item_id)
        if product is None:
            raise ValueError(f"Unknown product id `{item.item_id}`.")

        line_total = product.price_eur * item.quantity if product.price_eur is not None else None
        if line_total is None:
            missing_price_count += 1
        else:
            running_total += line_total

        hydrated_items.append(
            BundleProposalLineItem(
                item_id=item.item_id,
                product_name=product.product_name,
                display_title=product.display_title,
                product_url=product.url,
                description_text=product.description_text,
                price_eur=product.price_eur,
                quantity=item.quantity,
                line_total_eur=line_total,
                reason=item.reason,
                image_urls=list(
                    image_urls_for_runtime(
                        runtime=ctx.deps.runtime,
                        canonical_product_key=item.item_id,
                    )
                ),
            )
        )

    return hydrated_items, None if missing_price_count else running_total, missing_price_count


def _normalize_bundle_items(
    items: list[BundleProposalItemInput],
) -> tuple[list[BundleProposalItemInput], int]:
    deduped_order: list[str] = []
    merged_items: dict[str, BundleProposalItemInput] = {}
    duplicate_count = 0

    for item in items:
        existing = merged_items.get(item.item_id)
        if existing is None:
            deduped_order.append(item.item_id)
            merged_items[item.item_id] = item
            continue
        duplicate_count += 1
        merged_reason = f"{existing.reason.rstrip('.')}; {item.reason.strip()}"
        merged_items[item.item_id] = BundleProposalItemInput(
            item_id=item.item_id,
            quantity=existing.quantity + item.quantity,
            reason=merged_reason,
        )

    return [merged_items[item_id] for item_id in deduped_order], duplicate_count


def _validate_bundle_items_are_grounded(
    ctx: RunContext[SearchAgentDeps],
    items: list[BundleProposalItemInput],
) -> None:
    grounded_product_ids = ctx.deps.state.grounded_product_ids()
    if not grounded_product_ids:
        raise ValueError(
            "Bundle proposal requires grounded search results. "
            "Call `run_search_graph` first and only include returned products."
        )

    missing_product_ids = sorted(
        {item.item_id for item in items if item.item_id not in grounded_product_ids}
    )
    if not missing_product_ids:
        return

    joined_ids = ", ".join(f"`{product_id}`" for product_id in missing_product_ids)
    raise ValueError(
        "Bundle proposal can only include products returned by `run_search_graph`. "
        f"Ungrounded item ids: {joined_ids}."
    )


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


def _build_pricing_validation(*, missing_price_count: int) -> BundleValidationResult:
    if missing_price_count == 0:
        return BundleValidationResult(
            kind="pricing_complete",
            status="pass",
            message="All bundle items have prices, so the total is complete.",
        )
    noun = "item" if missing_price_count == 1 else "items"
    verb = "is" if missing_price_count == 1 else "are"
    return BundleValidationResult(
        kind="pricing_complete",
        status="warn",
        message=(
            f"{missing_price_count} {noun} {verb} missing prices, "
            "so the bundle total is incomplete."
        ),
    )


def _build_duplicate_item_validation(*, duplicate_count: int) -> BundleValidationResult:
    if duplicate_count == 0:
        return BundleValidationResult(
            kind="duplicate_items",
            status="pass",
            message="Each bundle product appears once.",
        )
    label = "entry" if duplicate_count == 1 else "entries"
    return BundleValidationResult(
        kind="duplicate_items",
        status="warn",
        message=f"Merged {duplicate_count} repeated product {label} into combined quantities.",
    )


def _build_bundle_validations(
    *,
    bundle_total: float | None,
    budget_cap_eur: float | None,
    duplicate_count: int,
    missing_price_count: int,
) -> list[BundleValidationResult]:
    validations = [
        _build_pricing_validation(missing_price_count=missing_price_count),
        _build_duplicate_item_validation(duplicate_count=duplicate_count),
    ]
    validations.extend(
        _build_budget_validations(bundle_total=bundle_total, budget_cap_eur=budget_cap_eur)
    )
    return validations


def _propose_bundle_with_services(
    ctx: RunContext[SearchAgentDeps],
    title: str,
    items: list[BundleProposalItemInput],
    notes: str | None = None,
    budget_cap_eur: float | None = None,
    *,
    services: SearchToolsetServices,
) -> BundleProposalToolResult:
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Bundle title must not be blank.")
    if not items:
        raise ValueError("Bundle proposal must include at least one item.")

    normalized_items, duplicate_count = _normalize_bundle_items(items)
    _validate_bundle_items_are_grounded(ctx, normalized_items)
    hydrated_items, bundle_total, missing_price_count = _hydrate_bundle_items(ctx, normalized_items)
    validations = _build_bundle_validations(
        bundle_total=bundle_total,
        budget_cap_eur=budget_cap_eur,
        duplicate_count=duplicate_count,
        missing_price_count=missing_price_count,
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
    ctx.deps.state.append_bundle_proposal(result)

    repository = services.get_search_repository(ctx.deps.runtime)
    if repository is not None:
        repository.record_bundle_proposal(
            thread_id=ctx.deps.state.thread_id or "anonymous-thread",
            run_id=ctx.deps.state.run_id,
            proposal=result,
        )

    validation_counts = Counter(validation.status for validation in validations)
    logger.info(
        "bundle_proposed",
        extra={
            "bundle_id": result.bundle_id,
            "bundle_item_count": len(result.items),
            "validation_fail_count": validation_counts.get("fail", 0),
            "validation_warn_count": validation_counts.get("warn", 0),
            "validation_unknown_count": validation_counts.get("unknown", 0),
            **telemetry_context(ctx.deps.state),
        },
    )
    return result


def _build_tool_failure_result(
    *,
    message: str,
    reason: str | None = None,
) -> ToolFailureResult:
    """Return a structured tool failure so the UI can render the error inline."""

    return ToolFailureResult(message=message, reason=reason)


def propose_bundle(
    ctx: RunContext[SearchAgentDeps],
    title: str,
    items: list[BundleProposalItemInput],
    notes: str | None = None,
    budget_cap_eur: float | None = None,
) -> BundleProposalToolResult | ToolFailureResult:
    """Hydrate and append one optional bundle proposal for search UI rendering."""

    try:
        return _propose_bundle_with_services(
            ctx,
            title,
            items,
            notes,
            budget_cap_eur,
            services=default_search_toolset_services(),
        )
    except ValueError as exc:
        logger.info(
            "bundle_proposal_rejected",
            extra={
                "reason": str(exc),
                **telemetry_context(ctx.deps.state),
            },
        )
        return _build_tool_failure_result(
            message="Bundle proposal could not be built.",
            reason=str(exc),
        )


def _list_room_3d_snapshot_context_with_services(
    ctx: RunContext[SearchAgentDeps],
    *,
    services: SearchToolsetServices,
) -> dict[str, object]:
    persisted: list[Room3DSnapshotEntry] = []
    repository = services.get_room_3d_repository(ctx.deps.runtime)
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


def list_room_3d_snapshot_context(ctx: RunContext[SearchAgentDeps]) -> dict[str, object]:
    """Return captured 3D snapshot context from state and persisted thread records."""

    return _list_room_3d_snapshot_context_with_services(
        ctx,
        services=default_search_toolset_services(),
    )


def build_search_toolset(
    services: SearchToolsetServices | None = None,
) -> FunctionToolset[SearchAgentDeps]:
    """Build toolset for search agent."""

    resolved_services = services or default_search_toolset_services()

    async def run_search_graph_tool(
        ctx: RunContext[SearchAgentDeps],
        queries: list[SearchQueryInput],
    ) -> SearchBatchToolResult:
        return await _run_search_graph_with_services(ctx, queries, services=resolved_services)

    def propose_bundle_tool(
        ctx: RunContext[SearchAgentDeps],
        title: str,
        items: list[BundleProposalItemInput],
        notes: str | None = None,
        budget_cap_eur: float | None = None,
    ) -> BundleProposalToolResult | ToolFailureResult:
        try:
            return _propose_bundle_with_services(
                ctx,
                title,
                items,
                notes,
                budget_cap_eur,
                services=resolved_services,
            )
        except ValueError as exc:
            logger.info(
                "bundle_proposal_rejected",
                extra={
                    "reason": str(exc),
                    **telemetry_context(ctx.deps.state),
                },
            )
            return _build_tool_failure_result(
                message="Bundle proposal could not be built.",
                reason=str(exc),
            )

    def list_room_3d_snapshot_context_tool(
        ctx: RunContext[SearchAgentDeps],
    ) -> dict[str, object]:
        return _list_room_3d_snapshot_context_with_services(
            ctx,
            services=resolved_services,
        )

    return FunctionToolset(
        tools=[
            build_remember_preference_tool(),
            Tool(run_search_graph_tool, name="run_search_graph"),
            Tool(propose_bundle_tool, name="propose_bundle"),
            Tool(
                list_room_3d_snapshot_context_tool,
                name="list_room_3d_snapshot_context",
            ),
        ]
    )
