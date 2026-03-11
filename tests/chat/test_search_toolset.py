from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast

from pydantic_ai import RunContext

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.search.toolset import propose_bundle
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import BundleProposalItemInput, RetrievalResult


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


def _run_context(*, price_eur: float | None) -> RunContext[SearchAgentDeps]:
    deps = SearchAgentDeps(
        runtime=cast(
            "ChatRuntime", _RuntimeStub(catalog_repository=_CatalogStub(price_eur=price_eur))
        ),
        attachment_store=cast("AttachmentStore", object()),
        state=SearchAgentState(thread_id="thread-1", run_id="run-1"),
    )
    return cast("RunContext[SearchAgentDeps]", SimpleNamespace(deps=deps))


def test_propose_bundle_appends_bundle_and_reports_budget_failure() -> None:
    ctx = _run_context(price_eur=20.0)

    result = propose_bundle(
        ctx,
        title="Desk seating bundle",
        budget_cap_eur=30.0,
        items=[BundleProposalItemInput(item_id="chair-1", quantity=2, reason="Seat for desk work")],
    )

    assert result.title == "Desk seating bundle"
    assert result.bundle_total_eur == 40.0
    assert result.items[0].line_total_eur == 40.0
    assert result.validations[0].status == "fail"
    assert ctx.deps.state.bundle_proposals[0]["bundle_id"] == result.bundle_id


def test_propose_bundle_reports_unknown_budget_when_prices_are_missing() -> None:
    ctx = _run_context(price_eur=None)

    result = propose_bundle(
        ctx,
        title="Concept bundle",
        budget_cap_eur=100.0,
        notes="Needs pricing follow-up.",
        items=[BundleProposalItemInput(item_id="chair-2", quantity=1, reason="Placeholder item")],
    )

    assert result.bundle_total_eur is None
    assert result.validations[0].status == "unknown"
    assert result.notes == "Needs pricing follow-up."
