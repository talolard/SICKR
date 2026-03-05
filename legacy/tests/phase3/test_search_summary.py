from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ikea_agent.phase3.repository import Phase3Repository, PromptRunEvent, PromptTurnEvent
from ikea_agent.phase3.search_summary import (
    SearchSummaryItem,
    SearchSummaryResponse,
    SearchSummaryService,
    SummaryCandidateProduct,
    SummaryModelRequest,
    build_summary_request,
)


@dataclass
class _RepoStub:
    prompt_runs: list[PromptRunEvent]
    prompt_turns: list[PromptTurnEvent]

    def __init__(self) -> None:
        self.prompt_runs = []
        self.prompt_turns = []

    def insert_prompt_run(self, event: PromptRunEvent) -> None:
        self.prompt_runs.append(event)

    def insert_prompt_turn(self, event: PromptTurnEvent) -> None:
        self.prompt_turns.append(event)


class _ServiceUnderTest(SearchSummaryService):
    captured_request: SummaryModelRequest | None
    captured_products: tuple[SummaryCandidateProduct, ...] | None

    def __init__(self, repository: _RepoStub) -> None:
        super().__init__(repository=cast("Phase3Repository", repository))
        self.captured_request = None
        self.captured_products = None

    def _render_template(  # type: ignore[override]
        self, *, template_key: str, template_version: str, context: dict[str, object]
    ) -> str:
        _ = (template_key, template_version, context)
        return "SYSTEM PROMPT"

    def _generate_response(  # type: ignore[override]
        self,
        *,
        query_text: str,
        request: SummaryModelRequest,
        products: tuple[SummaryCandidateProduct, ...],
        generation_config: dict[str, object],
    ) -> SearchSummaryResponse:
        _ = (query_text, generation_config)
        self.captured_request = request
        self.captured_products = products
        return SearchSummaryResponse(
            summary="ok",
            items=[
                SearchSummaryItem(
                    canonical_product_key=products[0].canonical_product_key,
                    item_name=products[0].item_name,
                    why="matched",
                )
            ],
        )


def test_build_summary_request_includes_products_and_user_query() -> None:
    products = (
        SummaryCandidateProduct(canonical_product_key="1-DE", item_name="Lamp"),
        SummaryCandidateProduct(canonical_product_key="2-DE", item_name="Shelf"),
    )
    request = build_summary_request(
        system_prompt="system",
        user_query="find compact options",
        products=products,
    )

    assert request.system_prompt == "system"
    assert "- 1-DE | Lamp" in request.user_prompt
    assert "- 2-DE | Shelf" in request.user_prompt
    assert "User query: find compact options" in request.user_prompt


def test_generate_passes_typed_products_into_summary_request_user_prompt() -> None:
    repository = _RepoStub()
    service = _ServiceUnderTest(repository=repository)
    products = (
        SummaryCandidateProduct(canonical_product_key="10-DE", item_name="MALM"),
        SummaryCandidateProduct(canonical_product_key="20-DE", item_name="SKUBB"),
    )

    _execution = service.generate(
        request_id="req-1",
        query_text="under-bed storage",
        products=products,
        template_key="summary-default",
        template_version="v1",
    )

    assert service.captured_request is not None
    assert service.captured_products == products
    assert "10-DE | MALM" in service.captured_request.user_prompt
    assert "20-DE | SKUBB" in service.captured_request.user_prompt
    assert "User query: under-bed storage" in service.captured_request.user_prompt
    assert len(repository.prompt_runs) == 1
    assert "10-DE | MALM" in repository.prompt_runs[0].user_prompt
