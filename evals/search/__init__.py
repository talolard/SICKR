"""Search-agent eval package.

Use `uv run python -m evals.search` to run the live eval harness quickly from the
command line. The assembled dataset is exposed here for programmatic use, while the
case definitions themselves live under `evals.search.datasets`.
"""

from evals.search.dataset import build_search_eval_dataset
from evals.search.harness import SearchAgentEvalHarness
from evals.search.types import SearchEvalInput, SearchEvalRunCapture

__all__ = [
    "SearchAgentEvalHarness",
    "SearchEvalInput",
    "SearchEvalRunCapture",
    "build_search_eval_dataset",
]
