from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast

import evals.search.harness as harness_module
import pytest
from evals.search.harness import SearchAgentEvalHarness
from evals.search.types import SearchEvalInput
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.shared.types import (
    BundleProposalLineItem,
    BundleProposalToolResult,
    BundleValidationResult,
)


@dataclass
class _FakeResult:
    output: str
    messages: list[ModelMessage]

    def new_messages(self) -> list[ModelMessage]:
        return list(self.messages)


@dataclass
class _FakeAgent:
    observed_user_prompt: str | None = "unexpected"
    observed_message_history: list[ModelMessage] | None = None
    observed_grounded_product_ids: set[str] | None = None

    async def run(
        self,
        user_prompt: str | None,
        *,
        deps: SearchAgentDeps,
        message_history: list[ModelMessage] | None = None,
    ) -> _FakeResult:
        self.observed_user_prompt = user_prompt
        self.observed_message_history = list(message_history or [])
        self.observed_grounded_product_ids = deps.state.grounded_product_ids()

        proposal = BundleProposalToolResult(
            bundle_id="bundle-test",
            title="Test bundle",
            notes="Structured continuation bundle.",
            budget_cap_eur=15000.0,
            items=[
                BundleProposalLineItem(
                    item_id="49513956-DE",
                    product_name="MITTZON",
                    display_title="MITTZON Desk Walnut Veneer Black S49513956",
                    product_url=None,
                    description_text="Desk",
                    price_eur=249.0,
                    quantity=3,
                    line_total_eur=747.0,
                    reason="One workstation per person.",
                    image_urls=[],
                )
            ],
            bundle_total_eur=747.0,
            validations=[
                BundleValidationResult(
                    kind="budget_max_eur",
                    status="pass",
                    message="Within budget.",
                )
            ],
            created_at="2026-03-20T15:31:50Z",
            run_id="eval-run",
        )
        deps.state.append_bundle_proposal(proposal)

        return _FakeResult(
            output="Bundle ready.",
            messages=[
                ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="propose_bundle",
                            args={"title": "Test bundle", "items": [{"item_id": "49513956-DE"}]},
                            tool_call_id="bundle-tool-call",
                        )
                    ],
                    model_name="test-model",
                    run_id="eval-run",
                ),
                ModelRequest(
                    parts=[
                        ToolReturnPart(
                            tool_name="propose_bundle",
                            content=proposal.model_dump(mode="json"),
                            tool_call_id="bundle-tool-call",
                        )
                    ],
                    run_id="eval-run",
                ),
                ModelResponse(
                    parts=[TextPart(content="Bundle ready.")],
                    model_name="test-model",
                    run_id="eval-run",
                ),
            ],
        )


def test_search_eval_harness_supports_bundle_continuation_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_agent = _FakeAgent()

    def _build_fake_agent(*, toolset_services: object | None = None) -> _FakeAgent:
        _ = toolset_services
        return fake_agent

    monkeypatch.setattr(
        harness_module,
        "build_search_agent",
        _build_fake_agent,
    )

    harness = SearchAgentEvalHarness()
    capture = asyncio.run(
        harness.capture_case(
            SearchEvalInput(
                user_message="Original Steuerberater brief.",
                continue_from_history=True,
                fixture_name="steuerberater_bundle_continuation",
            )
        )
    )

    assert fake_agent.observed_user_prompt is None
    observed_history = fake_agent.observed_message_history
    assert observed_history is not None
    assert len(observed_history) >= 5
    last_history_message = observed_history[-1]
    assert isinstance(last_history_message, ModelRequest)
    assert isinstance(last_history_message.parts[0], ToolReturnPart)

    grounded_product_ids = cast("set[str]", fake_agent.observed_grounded_product_ids)
    assert "49513956-DE" in grounded_product_ids
    assert "50496381-DE" in grounded_product_ids
    assert "9423217-DE" in grounded_product_ids

    assert [call.tool_name for call in capture.message_tool_calls] == ["propose_bundle"]
    assert [tool_return.tool_name for tool_return in capture.message_tool_returns] == [
        "propose_bundle"
    ]
    assert len(capture.bundle_proposals) == 1
    assert capture.bundle_proposals[0].title == "Test bundle"
