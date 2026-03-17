"""Eval dataset for search agent tool-call quality.

Uses pydantic_evals to verify the agent decomposes user queries into
well-structured ``run_search_graph`` calls with appropriate semantic
queries, filters, and creative expansions.

Run with:
    ALLOW_MODEL_REQUESTS=1 uv run pytest tests/chat/agents/search/test_search_evals.py -v -x
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

_RUBRIC_TEMPLATE = (
    "The agent's tool calls should demonstrate thoughtful query "
    "decomposition. Check that:\n"
    "1. The `run_search_graph` call contains multiple queries "
    "covering different aspects of the user's need (primary item, "
    "accessories, creative alternatives).\n"
    "2. The semantic_query strings are descriptive and leverage "
    "semantic meaning, not just keyword repetition.\n"
    "3. Filters (price, dimensions, exclude_keyword) are used "
    "where the input implies hard constraints.\n"
    "4. ALL of the following expected attributes are addressed by "
    "at least one query in the tool call:\n{expected_attributes}\n"
    "5. At least one query is a creative/lateral search that goes "
    "beyond the literal request (e.g., searching for adjacent "
    "product categories that solve the same problem).\n"
)

_JUDGE_MODEL = "google-gla:gemini-2.0-flash"


class SearchEvalInput(BaseModel):
    """User query plus expected solution attributes."""

    user_message: str
    expected_attributes: list[str]


@dataclass(frozen=True, slots=True)
class SearchEvalOutput:
    """Structured capture of the agent's tool calls."""

    tool_calls: list[ToolCallRecord]
    final_text: str


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """One tool call emitted by the agent during a run."""

    tool_name: str
    args: dict[str, object]


# ── Internal helpers ─────────────────────────────────────────────────


def _build_judge(attrs: list[str]) -> LLMJudge:
    formatted = _RUBRIC_TEMPLATE.format(
        expected_attributes="\n".join(f"  - {a}" for a in attrs),
    )
    return LLMJudge(
        rubric=formatted,
        include_input=True,
        model=_JUDGE_MODEL,
        score={"evaluation_name": "tool_call_quality"},
        assertion={
            "evaluation_name": "tool_call_pass",
            "include_reason": True,
        },
    )


def _case(
    name: str,
    user_message: str,
    attrs: list[str],
) -> Case[SearchEvalInput, SearchEvalOutput, None]:
    """Build one eval case with shared attributes."""
    return Case(
        name=name,
        inputs=SearchEvalInput(
            user_message=user_message,
            expected_attributes=attrs,
        ),
        evaluators=(_build_judge(attrs),),
    )


# ── Case attribute lists ────────────────────────────────────────────

_HALLWAY_ATTRS: list[str] = [
    "Wall-mounted sound absorption (panels, felt, hangings)",
    "Plants must be artificial or low-light (dark hallway)",
    "Wall-mounted rail/display to keep greenery off floor",
    "exclude_keyword filters out floor-based products",
    ("Creative query: e.g. cork tiles, woven tapestry, or upholstered panels as acoustic fix"),
]

_KIDS_ROOM_ATTRS: list[str] = [
    "Bunk bed or stacked sleeping solution to save space",
    "price filters with max_eur within €600 budget",
    "Storage (under-bed drawers, small shelving) for tiny room",
    "Dimension filters reflecting the 3m x 3m room",
    ("Creative query for dual-purpose furniture (e.g. bed with desk or storage stairs)"),
]

_BALCONY_ATTRS: list[str] = [
    "Depth filter max_cm: 80 on table/furniture queries",
    "Weather-resistant materials (metal, plastic, teak)",
    "Folding or wall-mounted table as space-saving option",
    "Stackable or foldable chairs for narrow space",
    ("Creative query: e.g. railing-mounted bar table or shelf doubling as dining surface"),
]

_CLOSET_OFFICE_ATTRS: list[str] = [
    "Width max 120cm, depth max 60cm dimension filters",
    "price filters capping spend around €350",
    "Desk surface/shelf fitting closet dimensions",
    "Wall-mounted shelving above desk",
    "Task lighting (LED/clamp) — exclude ceiling fixtures",
    ("Creative query: e.g. countertop as desk, or pegboard for wall organization"),
]

_BATHROOM_ATTRS: list[str] = [
    "exclude_keyword removes drilling/screw-mount products",
    "Suction-cup, adhesive, or over-door towel racks",
    "Free-standing or tension-rod shelf for toiletries",
    "Shower caddy (hanging or tension-pole style)",
    ("Creative query: e.g. ladder shelf against wall, or over-toilet storage unit"),
]


# ── Public API ───────────────────────────────────────────────────────


def build_search_eval_dataset() -> Dataset[SearchEvalInput, SearchEvalOutput, None]:
    """Build the 5-case eval dataset for search agent tool calling."""

    cases = [
        _case(
            "dark_hallway_plants_no_pets_on_floor",
            (
                "My hallway is really echoey and dark. I have two "
                "cats so nothing on the floor. I'd love some "
                "greenery on the walls."
            ),
            _HALLWAY_ATTRS,
        ),
        _case(
            "budget_kids_shared_bedroom_bunk",
            (
                "I need to set up a shared bedroom for two kids "
                "aged 4 and 7. The room is only 3m x 3m. "
                "Budget is tight, under €600 total."
            ),
            _KIDS_ROOM_ATTRS,
        ),
        _case(
            "tiny_balcony_dining_weatherproof",
            (
                "I have a narrow balcony, only 80cm deep. I want "
                "a small dining setup for two people that can "
                "handle rain."
            ),
            _BALCONY_ATTRS,
        ),
        _case(
            "closet_office_conversion",
            (
                "I want to turn a 120cm wide, 60cm deep closet "
                "into a home office. I need a desk surface, "
                "shelving above, and good lighting. Max €350."
            ),
            _CLOSET_OFFICE_ATTRS,
        ),
        _case(
            "rental_bathroom_no_drilling",
            (
                "I'm renting so I can't drill into the walls. "
                "My bathroom has zero storage. I need towel "
                "hanging, a shelf for toiletries, and something "
                "for the shower bottles."
            ),
            _BATHROOM_ATTRS,
        ),
    ]

    return Dataset[SearchEvalInput, SearchEvalOutput, None](
        name="search_agent_tool_call_quality",
        cases=cases,
    )
