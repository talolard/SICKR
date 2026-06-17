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

from evals.search.datasets.bundle_follow_through import build_bundle_follow_through_cases
from evals.search.datasets.bundle_realism import build_bundle_realism_cases
from evals.search.datasets.query_planning import build_query_planning_cases
from evals.search.evaluators import (
    BundleToolCallContractEvaluator,
    FinalOutputContractEvaluator,
    SearchToolCallContractEvaluator,
)
from evals.search.types import SearchEvalInput


def build_search_eval_dataset() -> Dataset[SearchEvalInput, str, None]:
    """Build the authoritative search-agent eval dataset."""

    return Dataset(
        name="search_agent_tool_call_quality",
        cases=[
            *build_query_planning_cases(),
            *build_bundle_follow_through_cases(),
            *build_bundle_realism_cases(),
        ],
        evaluators=[
            FinalOutputContractEvaluator(),
            SearchToolCallContractEvaluator(),
            BundleToolCallContractEvaluator(),
        ],
    )


__all__ = ["build_search_eval_dataset"]
