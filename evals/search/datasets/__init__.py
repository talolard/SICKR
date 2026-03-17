"""Search eval dataset package.

Quick run:

```bash
uv run python -m evals.search
```

Case definitions live in separate modules so search-planning scenarios and bundle-stage
follow-through scenarios can evolve independently while still assembling into one
authoritative dataset for the live harness.
"""

from __future__ import annotations

from pydantic_evals import Dataset
from pydantic_evals.evaluators import HasMatchingSpan, LLMJudge

from evals.base import LogfireToolCallLLMJudge
from evals.search.datasets.bundle_follow_through import build_bundle_follow_through_cases
from evals.search.datasets.common import (
    JUDGE_MODEL,
    RUN_SEARCH_GRAPH_SPAN_QUERY,
    SEARCH_RUBRIC,
)
from evals.search.datasets.query_planning import build_query_planning_cases
from evals.search.evaluators import (
    BundleToolCallContractEvaluator,
    FinalOutputContractEvaluator,
)
from evals.search.types import SearchEvalInput


def build_search_eval_dataset() -> Dataset[SearchEvalInput, str, None]:
    """Build the authoritative search-agent eval dataset."""

    return Dataset(
        name="search_agent_tool_call_quality",
        cases=[
            *build_query_planning_cases(),
            *build_bundle_follow_through_cases(),
        ],
        evaluators=[
            HasMatchingSpan(
                query=RUN_SEARCH_GRAPH_SPAN_QUERY,
                evaluation_name="called_run_search_graph",
            ),
            LogfireToolCallLLMJudge(
                tool_name="run_search_graph",
                judge=LLMJudge(
                    rubric=SEARCH_RUBRIC,
                    model=JUDGE_MODEL,
                    include_input=True,
                    score=False,
                    assertion={
                        "evaluation_name": "search_tool_call_quality",
                        "include_reason": True,
                    },
                ),
            ),
            FinalOutputContractEvaluator(),
            BundleToolCallContractEvaluator(),
        ],
    )


__all__ = ["build_search_eval_dataset"]
