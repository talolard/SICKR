"""Search-agent eval dataset and span-backed judges."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import HasMatchingSpan, LLMJudge

from evals.base import LogfireToolCallLLMJudge

JUDGE_MODEL = "google-gla:gemini-2.5-flash"
RUN_SEARCH_GRAPH_SPAN_QUERY = {
    "name_equals": "running tool",
    "has_attributes": {"gen_ai.tool.name": "run_search_graph"},
}
RUBRIC = """\
You are evaluating whether a search agent produced high-quality `run_search_graph`
tool calls for a home-furnishing request.

The input contains:
- the user message
- a list of expected attributes that must be addressed

The output contains:
- `tool_calls`: the captured `run_search_graph` tool calls from native PydanticAI spans
- `final_output`: the agent's final user-facing text

Grade PASS only if all of the following hold:
1. Every expected attribute is addressed by at least one query via semantic phrasing,
   structured filters, or exclusions.
2. The query set is solution-oriented rather than repetitive, covering the main product
   need plus useful adjacent or accessory searches where appropriate.
3. Hard constraints from the prompt are respected with reasonable filters or exclusions.
4. At least one query shows lateral or creative search reasoning beyond literal keyword
   repetition.

Grade FAIL if any expected attribute is entirely missing, if the query set is shallow or
repetitive, or if hard constraints such as size, price, or exclusions are ignored.
"""


@dataclass(frozen=True, slots=True)
class SearchEvalInput:
    """User request plus the rubric checklist for the judge."""

    user_message: str
    expected_attributes: list[str]


def _case(name: str, user_message: str, attrs: list[str]) -> Case[SearchEvalInput, str, None]:
    return Case(
        name=name,
        inputs=SearchEvalInput(
            user_message=user_message,
            expected_attributes=attrs,
        ),
    )


def build_search_eval_dataset() -> Dataset[SearchEvalInput, str, None]:
    """Build the authoritative search-agent eval dataset."""

    return Dataset(
        name="search_agent_tool_call_quality",
        cases=[
            _case(
                "pet_safe_dark_hallway",
                (
                    "My hallway is really echoey and dark. I have two dogs "
                    "that chew anything on the floor. I want it to feel more alive "
                    "maybe with greenery. Budget around €200 total."
                ),
                [
                    "At least one query targets sound-dampening wall solutions",
                    "Plants or greenery queries specify artificial or low-light varieties",
                    "Floor-level products are excluded via filters or semantic phrasing",
                    "A mounting or display system is included such as rails, hooks, or brackets",
                    "Price constraints respect the roughly €200 total budget",
                ],
            ),
            _case(
                "toddler_room_tight_gap",
                (
                    "We have a 75cm niche in the toddler's room. We need somewhere "
                    "to store clothes and change diapers. Max height 100cm because "
                    "there's a window above. Under €250."
                ),
                [
                    (
                        "Dimension filters enforce width less than or equal to 75cm "
                        "and height less than or equal to 100cm"
                    ),
                    "A changing-surface query exists such as a pad, mat, or changing top",
                    "An organizational add-on is included such as dividers, bins, or baskets",
                    "At least one creative query looks beyond nursery dresser phrasing",
                    "Primary furniture queries apply a price cap within €250",
                ],
            ),
            _case(
                "balcony_wfh_setup",
                (
                    "I want to set up a small outdoor workspace on my balcony. "
                    "It's about 100cm wide. Needs to survive rain when I'm not using "
                    "it. I'd like to keep it under €300."
                ),
                [
                    "Queries mention weather-resistant, outdoor, or waterproof materials",
                    "Width constraints at or below 100cm are respected",
                    "A foldable or compact desk or table query is present",
                    "Seating is addressed with an outdoor chair or stool",
                    "An accessory query exists such as storage, cover, or cable management",
                    "Indoor-only products are excluded by wording or filters",
                    "Price constraints reflect the €300 budget",
                ],
            ),
            _case(
                "reading_nook_under_stairs",
                (
                    "There's an awkward triangular space under my stairs about 120cm "
                    "wide at the base and it slopes down to nothing. I'd love a cozy "
                    "reading spot there. Something warm and inviting. Maybe €150 max."
                ),
                [
                    "At least one query targets seating suitable for a small awkward space",
                    "A lighting query is present",
                    "Soft textile queries exist such as throws, cushions, rugs, or blankets",
                    (
                        "Queries account for the sloped triangular shape with "
                        "low-profile or compact furniture"
                    ),
                    "A creative semantic query explores a non-obvious product category",
                    "Budget constraints stay within €150",
                ],
            ),
            _case(
                "rental_gallery_wall",
                (
                    "I rent my apartment and can't drill holes. I want a gallery wall "
                    "in my living room with photos, small shelves, and maybe a clock. "
                    "The wall is about 200cm wide. Under €180."
                ),
                [
                    "Queries specify no-drill, adhesive, or damage-free mounting methods",
                    "Drill or screw-based solutions are excluded",
                    "A picture-frame or photo-display query exists",
                    "A small shelf or ledge query exists",
                    "A decorative accent query exists such as a clock or mirror",
                    "At least one creative query leverages adhesive-friendly semantics",
                    "Price filters stay within €180",
                ],
            ),
        ],
        evaluators=[
            HasMatchingSpan(
                query=RUN_SEARCH_GRAPH_SPAN_QUERY,
                evaluation_name="called_run_search_graph",
            ),
            LogfireToolCallLLMJudge(
                tool_name="run_search_graph",
                judge=LLMJudge(
                    rubric=RUBRIC,
                    model=JUDGE_MODEL,
                    include_input=True,
                    score=False,
                    assertion={
                        "evaluation_name": "tool_call_quality",
                        "include_reason": True,
                    },
                ),
            ),
        ],
    )
