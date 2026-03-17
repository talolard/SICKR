"""Shared harness primitives for live agent evals."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import TypeVar

from pydantic_evals.evaluators import Evaluator, EvaluatorContext, LLMJudge

from evals.base.capture import extract_logfire_tool_call_captures
from evals.base.types import ToolCallJudgeOutput

InputsT = TypeVar("InputsT")
OutputT = TypeVar("OutputT")
DepsT = TypeVar("DepsT")
MetadataT = TypeVar("MetadataT")


class AgentEvalHarness[InputsT, OutputT](ABC):
    """Small reusable lifecycle for live agent eval harnesses."""

    @abstractmethod
    async def run_case(self, inputs: InputsT) -> OutputT:
        """Run one eval case and return the task output."""


class LogfireToolCallLLMJudge(Evaluator[InputsT, OutputT, MetadataT]):
    """Judge tool call quality from native Logfire span captures."""

    def __init__(self, *, tool_name: str, judge: LLMJudge) -> None:
        self.tool_name = tool_name
        self.judge = judge

    async def evaluate(
        self,
        ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
    ) -> object:
        """Evaluate one case using tool calls extracted from the span tree."""

        synthetic_output = ToolCallJudgeOutput(
            tool_calls=extract_logfire_tool_call_captures(ctx.span_tree, tool_name=self.tool_name),
            final_output=ctx.output,
        )
        synthetic_ctx = replace(ctx, output=synthetic_output)
        return await self.judge.evaluate_async(synthetic_ctx)
