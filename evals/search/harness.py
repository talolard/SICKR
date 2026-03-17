"""Direct, non-pytest harness for live search-agent evals."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from evals.base import AgentEvalHarness
from evals.search.dataset import SearchEvalInput
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

    def read_product_by_key(self, *, product_key: str) -> RetrievalResult | None:
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


@dataclass(frozen=True, slots=True)
class _SettingsStub:
    default_query_limit: int = 25


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    """Minimal runtime for search evals.

    Persistence is injected through services, so this stub intentionally stays small.
    """

    catalog_repository: _CatalogStub
    settings: _SettingsStub


@dataclass(frozen=True, slots=True)
class _SearchBatchStub:
    """Stub search runner that records normalized tool inputs in spans only."""

    async def __call__(
        self,
        *,
        runtime: ChatRuntime,
        queries: list[SearchQueryInput],
    ) -> SearchBatchToolResult:
        _ = runtime
        return SearchBatchToolResult(
            queries=[
                SearchQueryToolResult(
                    query_id=query.query_id,
                    semantic_query=query.semantic_query,
                    results=[],
                    total_candidates=0,
                    returned_count=0,
                )
                for query in queries
            ]
        )


def _build_toolset_services() -> SearchToolsetServices:
    return SearchToolsetServices(
        run_search_batch=_SearchBatchStub(),
        get_search_repository=lambda _runtime: None,
        get_room_3d_repository=lambda _runtime: None,
    )


def _build_stub_deps(root_dir: Path) -> SearchAgentDeps:
    return SearchAgentDeps(
        runtime=cast(
            "ChatRuntime",
            _RuntimeStub(
                catalog_repository=_CatalogStub(),
                settings=_SettingsStub(),
            ),
        ),
        attachment_store=AttachmentStore(root_dir),
        state=SearchAgentState(
            thread_id="eval-thread",
            run_id="eval-run",
        ),
    )


class SearchAgentEvalHarness(AgentEvalHarness[SearchEvalInput, str]):
    """Run the real search agent with infrastructure replaced at the toolset seam."""

    async def run_case(self, inputs: SearchEvalInput) -> str:
        """Execute one live search-agent run for the supplied eval case."""

        agent = build_search_agent(toolset_services=_build_toolset_services())
        with tempfile.TemporaryDirectory(prefix="search-eval-attachments-") as tmp_dir:
            deps = _build_stub_deps(Path(tmp_dir))
            result = await agent.run(inputs.user_message, deps=deps)
        return result.output
