"""Runner script for the search agent tool-call evals.

Why a separate runner?
----------------------
``eval_search_tool_calls.py`` defines the dataset, task function, and has its
own ``main()`` that prints verbose output (inputs + outputs).  This runner is a
thin wrapper that prints *only* the summary table — useful for quick
pass/fail checks during prompt iteration.

It also handles two practical issues:

1. **sys.path**: When run as ``python tests/.../run_eval.py`` the repo root
   may not be on ``sys.path``, so the ``tests`` package isn't importable.
   We prepend the repo root explicitly.

2. **ALLOW_MODEL_REQUESTS**: The repo's default is to block live model calls
   (safety for CI and accidental runs).  We set the env var so
   ``build_search_agent()`` constructs a real Gemini model instead of TestModel.
   ``override_allow_model_requests(True)`` also lifts pydantic-ai's runtime
   gate so model requests don't raise.

Usage::

    uv run python tests/chat/agents/search/run_eval.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `tests` package is importable
_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

os.environ.setdefault("ALLOW_MODEL_REQUESTS", "1")

from pydantic_ai.models import override_allow_model_requests  # noqa: E402

from tests.chat.agents.search.eval_search_tool_calls import (  # noqa: E402
    dataset,
    run_search_agent,
)


async def main() -> None:
    with override_allow_model_requests(True):
        report = await dataset.evaluate(
            run_search_agent,
            name="search_agent_tool_call_quality",
            max_concurrency=1,
        )

    report.print(include_input=False, include_output=False)


if __name__ == "__main__":
    asyncio.run(main())
