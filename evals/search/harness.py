"""Direct, non-pytest harness for live search-agent evals."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pydantic_ai.messages import ModelMessage

from evals.base import (
    AgentEvalHarness,
    extract_message_tool_call_captures,
    extract_message_tool_return_captures,
)
from evals.search.fixtures import SEARCH_EVAL_FIXTURES, SearchEvalFixture
from evals.search.types import SearchEvalInput, SearchEvalRunCapture
from ikea_agent.chat.agents.search.agent import build_search_agent
from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.search.toolset import SearchToolsetServices
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import (
    RetrievalResult,
    SearchBatchToolResult,
    SearchQueryInput,
    SearchQueryToolResult,
)


@dataclass(frozen=True, slots=True)
class _CatalogStub:
    """Catalog stub that keeps optional bundle calls from crashing the run."""

    products_by_key: dict[str, RetrievalResult]
    image_urls_by_key: dict[str, tuple[str, ...]]

    def read_product_by_key(self, *, product_key: str) -> RetrievalResult | None:
        product = self.products_by_key.get(product_key)
        if product is not None:
            return product
        return RetrievalResult(
            canonical_product_key=product_key,
            product_name=f"Stub product {product_key}",
            product_type="Furniture",
            description_text="Stub catalog entry for eval-only runs.",
            embedding_text=None,
            main_category="general",
            sub_category="general",
            dimensions_text="50x50x50",
            width_cm=50.0,
            depth_cm=50.0,
            height_cm=50.0,
            price_eur=50.0,
            url=None,
            semantic_score=0.0,
            filter_pass_reasons=(),
            rank_explanation="eval stub",
        )

    def read_image_urls_by_product_keys(
        self,
        *,
        canonical_product_keys: list[str],
        serving_strategy: str,
        base_url: str | None,
    ) -> dict[str, tuple[str, ...]]:
        _ = (serving_strategy, base_url)
        return {
            product_key: self.image_urls_by_key.get(product_key, ())
            for product_key in canonical_product_keys
        }


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25
    image_serving_strategy: str = "backend_proxy"
    image_service_base_url: str | None = None


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    """Minimal runtime for search evals.

    Persistence is injected through services, so this stub intentionally stays small.
    """

    catalog_repository: _CatalogStub
    settings: _SettingsStub


@dataclass(frozen=True, slots=True)
class _SearchBatchStub:
    """Stub search runner that can seed deterministic tool outputs per case."""

    fixture: SearchEvalFixture | None = None

    async def __call__(
        self,
        *,
        runtime: ChatRuntime,
        queries: list[SearchQueryInput],
    ) -> SearchBatchToolResult:
        _ = runtime
        query_results: list[SearchQueryToolResult] = []
        for query in queries:
            results = (
                self.fixture.resolve_results(query.semantic_query)
                if self.fixture is not None
                else []
            )
            query_results.append(
                SearchQueryToolResult(
                    query_id=query.query_id,
                    semantic_query=query.semantic_query,
                    results=results,
                    total_candidates=len(results),
                    returned_count=len(results),
                )
            )
        return SearchBatchToolResult(queries=query_results)


def _build_toolset_services(fixture: SearchEvalFixture | None) -> SearchToolsetServices:
    return SearchToolsetServices(
        run_search_batch=_SearchBatchStub(fixture=fixture),
        get_search_repository=lambda _runtime: None,
        get_room_3d_repository=lambda _runtime: None,
    )


def _fixture_catalog_products(fixture: SearchEvalFixture | None) -> dict[str, RetrievalResult]:
    if fixture is None:
        return {}
    unique_products: dict[str, RetrievalResult] = {}
    result_sets = [fixture.default_results]
    result_sets.extend(override.results for override in fixture.query_overrides)
    result_sets.extend(
        tuple(result for query in batch.queries for result in query.results)
        for batch in fixture.grounded_batches
    )
    for result_set in result_sets:
        for product in result_set:
            unique_products[product.product_id] = RetrievalResult(
                canonical_product_key=product.product_id,
                product_name=product.product_name,
                product_type=product.product_type,
                description_text=product.description_text,
                embedding_text=None,
                main_category=product.main_category,
                sub_category=product.sub_category,
                dimensions_text=None,
                width_cm=product.width_cm,
                depth_cm=product.depth_cm,
                height_cm=product.height_cm,
                price_eur=product.price_eur,
                url=product.url,
                semantic_score=1.0,
                filter_pass_reasons=(),
                rank_explanation="eval fixture",
                display_title=product.display_title,
            )
    return unique_products


def _fixture_image_urls(fixture: SearchEvalFixture | None) -> dict[str, tuple[str, ...]]:
    if fixture is None:
        return {}
    image_urls_by_key: dict[str, tuple[str, ...]] = {}
    result_sets = [fixture.default_results]
    result_sets.extend(override.results for override in fixture.query_overrides)
    result_sets.extend(
        tuple(result for query in batch.queries for result in query.results)
        for batch in fixture.grounded_batches
    )
    for result_set in result_sets:
        for product in result_set:
            image_urls_by_key[product.product_id] = product.image_urls
    return image_urls_by_key


def _build_stub_deps(root_dir: Path, *, fixture: SearchEvalFixture | None) -> SearchAgentDeps:
    return SearchAgentDeps(
        runtime=cast(
            "ChatRuntime",
            _RuntimeStub(
                catalog_repository=_CatalogStub(
                    products_by_key=_fixture_catalog_products(fixture),
                    image_urls_by_key=_fixture_image_urls(fixture),
                ),
                settings=_SettingsStub(),
            ),
        ),
        attachment_store=AttachmentStore(root_dir),
        state=SearchAgentState(
            project_id="eval-project",
            room_id="eval-room",
            room_title="Eval room",
            thread_id="eval-thread",
            run_id="eval-run",
        ),
    )


def _seed_fixture_history(
    deps: SearchAgentDeps,
    *,
    fixture: SearchEvalFixture | None,
) -> list[ModelMessage]:
    if fixture is None:
        return []
    for batch in fixture.grounded_batches:
        deps.state.remember_search_batch(batch)
    return list(fixture.message_history)


class SearchAgentEvalHarness(AgentEvalHarness[SearchEvalInput, str]):
    """Run the real search agent with infrastructure replaced at the toolset seam."""

    async def capture_case(self, inputs: SearchEvalInput) -> SearchEvalRunCapture:
        """Execute one live search-agent run and return the captured transcript artifacts."""

        fixture = SEARCH_EVAL_FIXTURES.get(inputs.fixture_name) if inputs.fixture_name else None
        agent = build_search_agent(toolset_services=_build_toolset_services(fixture))
        with tempfile.TemporaryDirectory(prefix="search-eval-attachments-") as tmp_dir:
            deps = _build_stub_deps(Path(tmp_dir), fixture=fixture)
            message_history = _seed_fixture_history(deps, fixture=fixture)
            user_prompt = None if inputs.continue_from_history else inputs.user_message
            result = await agent.run(
                user_prompt,
                deps=deps,
                message_history=message_history or None,
            )
            messages = result.new_messages()
            return SearchEvalRunCapture(
                final_output=result.output,
                message_tool_calls=extract_message_tool_call_captures(messages),
                message_tool_returns=extract_message_tool_return_captures(messages),
                bundle_proposals=list(deps.state.bundle_proposals),
            )

    async def run_case(self, inputs: SearchEvalInput) -> str:
        """Execute one live search-agent run for the supplied eval case."""

        capture = await self.capture_case(inputs)
        return capture.final_output
