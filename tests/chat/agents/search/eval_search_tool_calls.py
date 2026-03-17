"""Eval: search agent tool-call quality.

Architecture & Design Decisions
===============================

What we're testing
------------------
The search agent's *query decomposition* — given a natural-language user
request, does the agent produce a good set of ``run_search_graph`` tool calls
(semantic queries + structured filters)?  We are NOT testing retrieval quality
(embedding similarity, reranking, etc.) — only the agent's reasoning about
*what to search for*.

Why tool-call evals instead of end-to-end?
-------------------------------------------
The search agent's value is in how it breaks an ambiguous lifestyle request
into multiple targeted queries with correct filters.  That decomposition is
the hardest part to get right and the most sensitive to prompt changes.  By
isolating it we can iterate on the prompt and measure improvement without
needing a running vector DB, embedder, or reranker.

Why ``pydantic_evals`` + ``LLMJudge``?
---------------------------------------
Tool-call quality is hard to express as deterministic assertions (did the agent
use *exactly* ``exclude_keyword="floor"`` vs. phrasing the semantic query to
avoid floors?  both are valid).  An LLM judge can evaluate whether a set of
queries *collectively* satisfies a rubric, tolerating the many valid ways the
agent can express the same intent.  ``pydantic_evals.Dataset`` gives us a
structured framework: typed inputs/outputs, per-case evaluators, a progress
bar, and a summary table.

Why stub the search pipeline?
-----------------------------
``run_search_graph`` (the tool the agent calls) delegates to
``run_search_pipeline_batch`` which needs a live Milvus index, embedder, and
DuckDB catalog.  We don't need real search results — we just want to see what
queries the agent *decided* to issue.  The stub intercepts the pipeline call,
records the ``SearchQueryInput`` objects, and returns empty results.  The agent
then sees zero results and writes a "no matches found" summary, which is fine
— we're grading the queries, not the response.

Why monkeypatch the toolset module?
------------------------------------
The toolset imports ``run_search_pipeline_batch`` at module load time::

    from ikea_agent.chat.search_pipeline import run_search_pipeline_batch

This binds a direct reference in the toolset module's namespace.  Patching the
*original* module (``search_pipeline.run_search_pipeline_batch``) would not
affect the already-bound name.  So we patch the reference *in the toolset
module* (``_toolset_mod.run_search_pipeline_batch``).  We restore the original
after each run to avoid cross-contamination.

Why ``max_concurrency=1``?
--------------------------
The monkeypatch swaps a module-level reference.  If two eval cases ran
concurrently, they'd race on that reference — one case could restore the
original while another is still running with the stub.  Sequential execution
avoids this.  (An alternative would be dependency-injection through the agent
deps, but that would require changing production code for eval ergonomics.)

Why ``MagicMock(spec=[...])`` for the runtime?
-----------------------------------------------
The search agent's toolset also calls ``search_repository(runtime)`` and
``room_3d_repository(runtime)`` which check ``hasattr(runtime, "session_factory")``.
A plain ``MagicMock()`` has *every* attribute, so those helpers would create
real ``SearchRepository`` / ``Room3DRepository`` instances backed by a mock
session factory, which then fails when SQLAlchemy tries to use it.  Using
``spec=["settings", "catalog_repository"]`` restricts the mock to only those
attributes, so ``hasattr(runtime, "session_factory")`` returns ``False`` and
the repository helpers return ``None``.

Eval case design
----------------
Each case is a realistic user query *different from* the prompt's built-in
scenarios but testing the same reasoning patterns:

- **pet_safe_dark_hallway**: tests constraint exclusion (floor items), budget
  filters, and creative lateral queries (artificial plants, acoustic panels).
- **toddler_room_tight_gap**: tests hard dimension filters (width ≤ 75cm,
  height ≤ 100cm), cross-category creative search, and add-on bundling.
- **balcony_wfh_setup**: tests material constraints (weather-resistant),
  multi-product bundling (desk + chair + accessories), and exclusion filters.
- **reading_nook_under_stairs**: tests handling unusual spatial shapes,
  low-profile/compact products, creative category leaps (meditation cushion).
- **rental_gallery_wall**: tests negative constraints (no drilling), multiple
  product categories in one solution, and adhesive/damage-free semantics.

``expected_attributes`` are human-written claims about what good queries should
contain.  The LLM judge checks each attribute against the actual tool calls.

Running
-------
::

    # From repo root, with GEMINI_API_KEY set:
    uv run python tests/chat/agents/search/run_eval.py

    # Or via module:
    ALLOW_MODEL_REQUESTS=1 uv run python -m tests.chat.agents.search.eval_search_tool_calls

Each case takes ~30-40s (one Gemini generation call for the agent + one for the 
judge).  Total wall time is ~3 minutes sequential.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models import override_allow_model_requests
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from ikea_agent.chat.agents.search.agent import (
    build_search_agent,
)
from ikea_agent.chat.agents.search.deps import SearchAgentDeps
from ikea_agent.chat.agents.state import SearchAgentState
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import (
    SearchBatchToolResult,
    SearchQueryInput,
    SearchQueryToolResult,
)


# ---------------------------------------------------------------------------
# Eval input / output types
#
# pydantic_evals.Dataset is generic over (InputT, OutputT).  The task
# function receives InputT and must return OutputT.  Evaluators see both.
# We pack the expected_attributes into InputT so the LLM judge can see
# them (via include_input=True) without needing expected_output.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalInput:
    """What the user asked, plus the checklist the judge grades against."""

    user_message: str
    expected_attributes: list[str]


@dataclass(frozen=True)
class EvalOutput:
    """What the agent did: the raw tool-call JSON and its final text.

    tool_calls_json is the primary grading surface — the judge checks
    whether these queries address all expected_attributes.
    agent_response is included for context but isn't the main signal.
    """

    tool_calls_json: str  # JSON-serialised list of SearchQueryInput dicts
    agent_response: str


# ---------------------------------------------------------------------------
# Pipeline stub
#
# Returns empty results for every query.  The agent will see
# returned_count=0 for all queries and respond with a "no matches"
# message — that's fine, we only care about *which* queries it chose.
# ---------------------------------------------------------------------------


def _make_empty_batch_result(
    queries: list[SearchQueryInput],
) -> SearchBatchToolResult:
    return SearchBatchToolResult(
        queries=[
            SearchQueryToolResult(
                query_id=q.query_id,
                semantic_query=q.semantic_query,
                results=[],
                total_candidates=0,
                returned_count=0,
            )
            for q in queries
        ]
    )


# ---------------------------------------------------------------------------
# Task function
#
# This is the callable that pydantic_evals passes each Case.inputs to.
# It must return EvalOutput.  Internally it:
#   1. Builds a fresh agent instance (so prompt changes take effect)
#   2. Creates stub deps (no real DB/Milvus/embedder needed)
#   3. Patches the pipeline to capture SearchQueryInput objects
#   4. Runs the agent and collects the tool calls from two sources:
#      - captured_queries: typed dataclasses from the stub
#      - message history: raw JSON args (fallback)
# ---------------------------------------------------------------------------


def _build_stub_deps() -> SearchAgentDeps:
    """Create minimal deps with stubbed runtime and attachment store.

    The runtime mock deliberately lacks ``session_factory`` so that
    ``search_repository()`` / ``room_3d_repository()`` return ``None``
    rather than constructing real repositories over a MagicMock session.
    """
    runtime = MagicMock(spec=["settings", "catalog_repository"])
    runtime.settings = MagicMock()
    runtime.settings.default_query_limit = 20
    # catalog_repository.read_product_by_key returns None (unknown product)
    # so propose_bundle will raise ValueError rather than hitting real DB
    runtime.catalog_repository.read_product_by_key.return_value = None
    attachment_store = AttachmentStore(
        root_dir=Path(tempfile.mkdtemp()),
        asset_repository=None,
    )
    state = SearchAgentState()
    return SearchAgentDeps(
        runtime=runtime,
        attachment_store=attachment_store,
        state=state,
    )


async def run_search_agent(inputs: EvalInput) -> EvalOutput:
    """Run the search agent on *inputs* and return captured tool calls."""
    agent = build_search_agent()
    deps = _build_stub_deps()

    # Monkeypatch the toolset's pipeline reference to capture queries
    import ikea_agent.chat.agents.search.toolset as _toolset_mod

    captured_queries: list[SearchQueryInput] = []
    _original_fn = _toolset_mod.run_search_pipeline_batch

    async def _stub_pipeline(
        runtime: Any,
        queries: Any,
    ) -> SearchBatchToolResult:
        captured_queries.extend(queries)
        return _make_empty_batch_result(queries)

    _toolset_mod.run_search_pipeline_batch = _stub_pipeline  # type: ignore[assignment]
    try:
        result = await agent.run(inputs.user_message, deps=deps)
    finally:
        _toolset_mod.run_search_pipeline_batch = _original_fn  # type: ignore[assignment]

    # Also extract tool calls from the message history
    tool_call_args: list[dict[str, Any]] = []
    for msg in result.all_messages():
        for part in msg.parts:
            if isinstance(part, ToolCallPart) and part.tool_name == "run_search_graph":
                args = part.args if isinstance(part.args, dict) else json.loads(part.args)
                tool_call_args.append(args)

    # Prefer captured queries (typed) over raw message args
    if captured_queries:
        serialized = [asdict(q) for q in captured_queries]
    elif tool_call_args:
        serialized = tool_call_args
    else:
        serialized = []

    return EvalOutput(
        tool_calls_json=json.dumps(serialized, indent=2, default=str),
        agent_response=result.output,
    )


# ---------------------------------------------------------------------------
# Eval cases
# ---------------------------------------------------------------------------

CASES: list[Case[EvalInput, EvalOutput]] = [
    # ── 1. Pet-safe dark hallway ──────────────────────────────────────
    Case(
        name="pet_safe_dark_hallway",
        inputs=EvalInput(
            user_message=(
                "My hallway is really echoey and dark. I have two dogs "
                "that chew anything on the floor. I want it to feel "
                "more alive — maybe greenery? Budget around €200 total."
            ),
            expected_attributes=[
                "At least one query targets sound-dampening wall solutions",
                "Plants/greenery queries specify artificial OR low-light varieties",
                "Floor-level products are excluded (via exclude_keyword or semantic phrasing)",
                "A mounting/display system is included (rails, hooks, or brackets)",
                "Price filters are present and respect the ~€200 total budget",
            ],
        ),
    ),
    # ── 2. Toddler room under tight dimensions ───────────────────────
    Case(
        name="toddler_room_tight_gap",
        inputs=EvalInput(
            user_message=(
                "We have a 75cm niche in the toddler's room. We need "
                "somewhere to store clothes and change diapers. Max height "
                "100cm because there's a window above. Under €250."
            ),
            expected_attributes=[
                "Dimension filters enforce width ≤ 75cm and height ≤ 100cm",
                "A changing-surface query exists (pad, mat, or changing top)",
                "An organizational add-on is included (dividers, bins, baskets)",
                "At least one creative/lateral query looks beyond 'nursery dresser' "
                "(e.g. 'compact chest of drawers', 'small sideboard')",
                "Price cap ≤ €250 is applied on primary furniture queries",
            ],
        ),
    ),
    # ── 3. Balcony work-from-home ─────────────────────────────────────
    Case(
        name="balcony_wfh_setup",
        inputs=EvalInput(
            user_message=(
                "I want to set up a small outdoor workspace on my balcony. "
                "It's about 100cm wide. Needs to survive rain when I'm not "
                "using it. I'd like to keep it under €300."
            ),
            expected_attributes=[
                "Queries mention weather-resistant, outdoor, or waterproof materials",
                "Width constraint ≤ 100cm is applied via dimension filters",
                "A foldable or compact desk/table query is present",
                "Seating is addressed (outdoor chair or stool)",
                "An accessory query exists — e.g. storage, cable management, or cover",
                "Indoor-only terms are excluded (e.g. exclude_keyword 'indoor' or similar)",
                "Price constraints reflect the €300 budget",
            ],
        ),
    ),
    # ── 4. Cozy reading nook under stairs ─────────────────────────────
    Case(
        name="reading_nook_under_stairs",
        inputs=EvalInput(
            user_message=(
                "There's an awkward triangular space under my stairs — "
                "about 120cm wide at the base, slopes down to nothing. "
                "I'd love a cozy reading spot there. Something warm and "
                "inviting. Maybe €150 max."
            ),
            expected_attributes=[
                "At least one query targets seating suitable for small/awkward spaces "
                "(floor cushion, bean bag, low bench, or similar)",
                "A lighting query is present (reading lamp, clip light, LED strip)",
                "Textile/softness queries exist (throw, cushion, rug, blanket)",
                "Queries account for the sloped/triangular shape constraint "
                "(low-profile furniture, compact dimensions)",
                "A creative semantic query explores non-obvious product categories "
                "(e.g. 'meditation cushion', 'kids lounge seat', 'upholstered floor mat')",
                "Budget ≤ €150 is applied",
            ],
        ),
    ),
    # ── 5. Rental-friendly gallery wall ───────────────────────────────
    Case(
        name="rental_gallery_wall",
        inputs=EvalInput(
            user_message=(
                "I rent my apartment and can't drill holes. I want to "
                "create a gallery wall in my living room — mix of photos, "
                "small shelves, and maybe a clock. About 200cm wide wall. "
                "Under €180."
            ),
            expected_attributes=[
                "Queries specify no-drill / adhesive / damage-free mounting methods",
                "Nail and screw based solutions are excluded "
                "(exclude_keyword 'drill', 'screw', or similar phrasing)",
                "A picture frame or photo display query exists",
                "A small shelf query exists (floating shelf, picture ledge)",
                "A decorative accent query exists (clock, mirror, or similar)",
                "At least one creative query leverages semantics "
                "(e.g. 'adhesive wall gallery kit', 'command strip compatible shelf')",
                "Price filters stay within €180",
            ],
        ),
    ),
]

# ---------------------------------------------------------------------------
# Dataset + evaluator
#
# The rubric tells the LLM judge *how* to grade.  It sees:
#   - <Input>: EvalInput (user_message + expected_attributes)
#   - <Output>: EvalOutput (tool_calls_json + agent_response)
# The judge returns pass/fail + a reason string.
# ---------------------------------------------------------------------------

JUDGE_RUBRIC = """\
You are evaluating whether a search agent produced high-quality tool calls
(semantic search queries with filters) for a home-furnishing user request.

The user's message and the expected solution attributes are provided in the input.
The output contains the actual tool calls the agent made (as JSON) and its text response.

Grade PASS if ALL of the following hold:
1. Every expected attribute listed in the input is addressed by at least one query
   (via semantic_query phrasing, filter fields, or exclude_keyword).
2. The queries together form a coherent "solution bundle" — not just
   a single literal search, but a set that covers the anchor product,
   necessary add-ons, and at least one creative/lateral search.
3. Filters use the correct field names and reasonable values
   (dimensions, price, exclude_keyword, include_keyword, sort).
4. At least one query uses a creative semantic phrasing that goes beyond
   the literal words in the user's request.

Grade FAIL if any expected attribute is completely unaddressed, if the
queries are trivially repetitive, or if hard constraints (dimensions, budget)
are ignored.
"""

dataset: Dataset[EvalInput, EvalOutput] = Dataset(
    cases=CASES,
    evaluators=[
        LLMJudge(
            rubric=JUDGE_RUBRIC,
            # Use flash for the judge — cheaper than the agent's model,
            # fast enough for pass/fail rubric grading.
            model="google-gla:gemini-2.5-flash",
            # include_input=True sends EvalInput (with expected_attributes)
            # to the judge so it knows what to check for.
            include_input=True,
            # We don't use expected_output — the attributes are in the input.
            include_expected_output=False,
        ),
    ],
)


# ---------------------------------------------------------------------------
# Main: run evals
# ---------------------------------------------------------------------------


async def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY or GOOGLE_API_KEY to run evals.", file=sys.stderr)
        sys.exit(1)

    # Allow live model requests for the eval run
    os.environ.setdefault("ALLOW_MODEL_REQUESTS", "1")

    with override_allow_model_requests(True):
        report = await dataset.evaluate(
            run_search_agent,
            name="search_agent_tool_call_quality",
            max_concurrency=1,
        )

    report.print(include_input=True, include_output=True)


if __name__ == "__main__":
    asyncio.run(main())
