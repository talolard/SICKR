"""Search agent tool-call quality evals.

Run with:
    ALLOW_MODEL_REQUESTS=1 uv run pytest \
        tests/chat/agents/search/test_search_evals.py -v -x

Requires GEMINI_API_KEY (the search agent and LLMJudge both call
a live model).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models import override_allow_model_requests

import ikea_agent.chat.agents.search.toolset as toolset_mod
from ikea_agent.chat.agents.search.agent import build_search_agent
from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.config import get_settings
from ikea_agent.shared.types import (
    SearchBatchToolResult,
    SearchQueryInput,
    SearchQueryToolResult,
    ShortRetrievalResult,
)

from .eval_dataset import (
    SearchEvalInput,
    SearchEvalOutput,
    ToolCallRecord,
    build_search_eval_dataset,
)

# ── Stubs ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class _CatalogStub:
    """Minimal catalog — evals only test tool *calling*."""

    def read_product_by_key(
        self,
        *,
        product_key: str,  # noqa: ARG002
    ) -> None:
        return None


@dataclass(frozen=True, slots=True)
class _RuntimeStub:
    """Minimal runtime stub for eval runs."""

    catalog_repository: _CatalogStub = _CatalogStub()
    settings: object = None
    sqlalchemy_engine: object = None
    session_factory: object = None
    embedder: object = None
    milvus_service: object = None
    reranker: object = None


@dataclass(slots=True)
class _PipelineCapture:
    """Replaces the real pipeline — returns stub results."""

    captured: list[list[SearchQueryInput]] = field(
        default_factory=list,
    )

    async def __call__(
        self,
        *,
        runtime: object,  # noqa: ARG002
        queries: list[SearchQueryInput],
    ) -> SearchBatchToolResult:
        self.captured.append(queries)
        return SearchBatchToolResult(
            queries=[
                SearchQueryToolResult(
                    query_id=q.query_id,
                    semantic_query=q.semantic_query,
                    results=[
                        ShortRetrievalResult(
                            product_id=f"{q.query_id}-stub",
                            product_name=f"Stub: {q.query_id}",
                            product_type="furniture",
                            description_text="Stub result.",
                            main_category="general",
                            sub_category="general",
                            width_cm=50.0,
                            depth_cm=50.0,
                            height_cm=50.0,
                            price_eur=49.99,
                        ),
                    ],
                    total_candidates=10,
                    returned_count=1,
                )
                for q in queries
            ],
        )


# ── Helpers ──────────────────────────────────────────────────────────


def _model_requests_available() -> bool:
    """Check if live model requests are configured."""
    try:
        s = get_settings()
        return bool(s.allow_model_requests and s.gemini_api_key)
    except Exception:
        return False


def _extract_tool_calls(
    result: object,
) -> list[ToolCallRecord]:
    """Pull tool-call parts from the agent message history."""
    records: list[ToolCallRecord] = []
    messages = result.all_messages()  # type: ignore[attr-defined]
    for msg in messages:
        if not isinstance(msg, ModelResponse):
            continue
        for part in msg.parts:
            if isinstance(part, ToolCallPart):
                args: dict[str, object] = (
                    part.args if isinstance(part.args, dict) else json.loads(part.args or "{}")
                )
                records.append(
                    ToolCallRecord(
                        tool_name=part.tool_name,
                        args=args,
                    ),
                )
    return records


def _build_stub_deps() -> SearchAgentDeps:
    return SearchAgentDeps(
        runtime=cast("ChatRuntime", _RuntimeStub()),
        attachment_store=cast("AttachmentStore", object()),
        state=SearchAgentState(
            thread_id="eval-thread",
            run_id="eval-run",
        ),
    )


# ── Eval task ────────────────────────────────────────────────────────


async def _search_agent_task(
    inputs: SearchEvalInput,
) -> SearchEvalOutput:
    """Run the search agent, capture tool calls."""
    capture = _PipelineCapture()
    original_fn = toolset_mod.run_search_pipeline_batch

    # Patch where the toolset actually references the pipeline
    toolset_mod.run_search_pipeline_batch = capture  # type: ignore[assignment]
    try:
        agent: Agent[SearchAgentDeps, str] = build_search_agent()
        deps = _build_stub_deps()
        result = await agent.run(inputs.user_message, deps=deps)
        tool_calls = _extract_tool_calls(result)
        return SearchEvalOutput(
            tool_calls=tool_calls,
            final_text=result.output,
        )
    finally:
        toolset_mod.run_search_pipeline_batch = original_fn  # type: ignore[assignment]


# ── Pytest entry ─────────────────────────────────────────────────────


@pytest.mark.skipif(
    not _model_requests_available(),
    reason=("Live model requests disabled (set ALLOW_MODEL_REQUESTS=1 and GEMINI_API_KEY)"),
)
@pytest.mark.anyio
async def test_search_agent_tool_call_evals() -> None:
    """Evaluate search agent tool-call decomposition quality."""
    dataset = build_search_eval_dataset()
    with override_allow_model_requests(True):
        report = await dataset.evaluate(
            _search_agent_task,
            name="search_tool_call_quality",
            max_concurrency=2,
        )
    report.print(include_input=True, include_output=True)

    for case in report.cases:
        for label, result in case.scores.items():
            if hasattr(result, "value") and result.value is False:
                reason = getattr(result, "reason", "no reason")
                pytest.fail(
                    f"Case {case.name!r} failed {label}: {reason}",
                )
