"""Search-agent eval dataset and span-backed judges."""

from __future__ import annotations

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import HasMatchingSpan, LLMJudge

from evals.base import LogfireToolCallLLMJudge
from evals.search.evaluators import (
    BundleToolCallContractEvaluator,
    FinalOutputContractEvaluator,
)
from evals.search.types import SearchEvalInput

JUDGE_MODEL = "google-gla:gemini-2.5-flash"
RUN_SEARCH_GRAPH_SPAN_QUERY = {
    "name_equals": "running tool",
    "has_attributes": {"gen_ai.tool.name": "run_search_graph"},
}
SEARCH_RUBRIC = """\
You are evaluating whether a search agent produced high-quality `run_search_graph`
tool calls for a home-furnishing request.

The input contains:
- the user message
- `expected_search_attributes`: a list of must-address search requirements

The output contains:
- `tool_calls`: the captured `run_search_graph` tool calls from native PydanticAI spans
- `final_output`: the agent's final user-facing text

Grade PASS only if all of the following hold:
1. Every expected search attribute is addressed by at least one query via semantic phrasing,
   structured filters, or exclusions.
2. The query set is solution-oriented rather than repetitive, covering the main product
   need plus useful adjacent or accessory searches where appropriate.
3. Hard constraints from the prompt are respected with reasonable filters or exclusions.
4. At least one query shows lateral or creative search reasoning beyond literal keyword
   repetition.

Grade FAIL if any expected attribute is entirely missing, if the query set is shallow or
repetitive, or if hard constraints such as size, price, or exclusions are ignored.
"""
BUNDLE_RUBRIC = """\
You are evaluating whether a search agent produced a high-quality `propose_bundle`
tool call after retrieval.

The input contains:
- the user message
- `expected_bundle_attributes`: bundle requirements that should appear in the proposal
- `forbidden_bundle_attributes`: bundle elements that should not appear
- `source_thread_id`: optional grounding reference for the originating conversation

The output contains:
- `tool_calls`: the captured `propose_bundle` tool calls from native PydanticAI spans
- `final_output`: the agent's final user-facing text

Grade PASS only if all of the following hold:
1. At least one `propose_bundle` call is present when `expected_bundle_attributes` is non-empty.
2. Every expected bundle attribute is covered by the bundle title, line items, or per-item reasons.
3. No forbidden bundle attribute appears in the proposed items, title, or notes.
4. The bundle reflects a coherent solution to the user's request rather than unrelated products.

Grade FAIL if the bundle omits required complementary products, includes forbidden products,
or shows no bundle call despite bundle-stage expectations.
"""


def _bundle_case_evaluators() -> tuple[object, ...]:
    return (
        LogfireToolCallLLMJudge(
            tool_name="propose_bundle",
            judge=LLMJudge(
                rubric=BUNDLE_RUBRIC,
                model=JUDGE_MODEL,
                include_input=True,
                score=False,
                assertion={
                    "evaluation_name": "bundle_tool_call_quality",
                    "include_reason": True,
                },
            ),
        ),
    )


def _case(
    name: str,
    user_message: str,
    search_attrs: list[str],
    *,
    bundle_attrs: list[str] | None = None,
    forbidden_bundle_attrs: list[str] | None = None,
    forbidden_response_terms: list[str] | None = None,
    fixture_name: str | None = None,
    source_thread_id: str | None = None,
    require_bundle_call: bool = False,
    forbid_bundle_call: bool = False,
) -> Case[SearchEvalInput, str, None]:
    case_evaluators: tuple[object, ...] = ()
    if bundle_attrs:
        case_evaluators = _bundle_case_evaluators()
    return Case(
        name=name,
        inputs=SearchEvalInput(
            user_message=user_message,
            expected_search_attributes=search_attrs,
            expected_bundle_attributes=list(bundle_attrs or []),
            forbidden_bundle_attributes=list(forbidden_bundle_attrs or []),
            forbidden_response_terms=list(forbidden_response_terms or []),
            fixture_name=fixture_name,
            source_thread_id=source_thread_id,
            require_bundle_call=require_bundle_call,
            forbid_bundle_call=forbid_bundle_call,
        ),
        evaluators=case_evaluators,
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
                search_attrs=[
                    "Queries specify no-drill, adhesive, or damage-free mounting methods",
                    "Drill or screw-based solutions are excluded",
                    "A picture-frame or photo-display query exists",
                    "A small shelf or ledge query exists",
                    "A decorative accent query exists such as a clock or mirror",
                    "At least one creative query leverages adhesive-friendly semantics",
                    "Price filters stay within €180",
                ],
                bundle_attrs=[
                    (
                        "The proposed bundle includes photo-display products grounded "
                        "in the query results"
                    ),
                    (
                        "The proposed bundle includes a small shelf or ledge grounded "
                        "in the query results"
                    ),
                    "The proposed bundle includes a decorative accent such as a clock",
                    "The bundle reflects renter-safe mounting rather than drill-only setup",
                ],
                fixture_name="gallery_wall_bundle_seed",
                require_bundle_call=True,
            ),
            _case(
                "search_reply_avoids_bundle_word",
                (
                    "Please help me find a renter-safe gallery wall with framed photos, "
                    "a tiny ledge, and one decorative accent under €180."
                ),
                search_attrs=[
                    "Queries cover renter-safe mounting methods",
                    "Queries include photos or frames plus a ledge and decorative accent",
                ],
                forbidden_response_terms=["bundle"],
            ),
            _case(
                "hallway_thread_complementary_products",
                (
                    "Hi we have a long hallway, it like 7 by 1.8 and I want to add more "
                    "lighting to it, but we dont have many plugs and I dont want to run "
                    "a bunch of cables."
                ),
                search_attrs=[
                    (
                        "Queries include portable or battery-powered lighting rather "
                        "than wired-only fixtures"
                    ),
                    (
                        "Queries include complementary support products such as "
                        "floating shelves or a console table"
                    ),
                    "Queries include adhesive or no-drill mounting approaches where relevant",
                ],
                bundle_attrs=[
                    "The bundle includes portable lighting products",
                    (
                        "The bundle includes at least one complementary support "
                        "product such as a shelf or console table"
                    ),
                    (
                        "The bundle includes or reflects a no-drill or "
                        "adhesive-friendly mounting approach"
                    ),
                ],
                fixture_name="hallway_complementary_seed",
                source_thread_id="agent_search-286fe4b8",
                require_bundle_call=True,
            ),
            _case(
                "hallway_complementary_omission_guard",
                (
                    "Could you make me a hallway lighting solution with portable lamps, "
                    "somewhere to place them, and minimal drilling? I still want it to "
                    "look intentional, not like random lights on the floor."
                ),
                search_attrs=[
                    "Queries cover portable lighting for a hallway",
                    (
                        "Queries cover complementary placement products such as "
                        "shelves or a narrow table"
                    ),
                    "Queries explore no-drill or low-drill setup options",
                ],
                bundle_attrs=[
                    "The bundle includes portable lighting",
                    (
                        "The bundle includes a complementary placement product instead "
                        "of leaving lamps unsupported"
                    ),
                ],
                fixture_name="hallway_complementary_seed",
                source_thread_id="agent_search-286fe4b8",
                require_bundle_call=True,
            ),
            _case(
                "unsupported_constraints_do_not_bundle",
                (
                    "Could you make me a second bundle that includes, I think, some adhesive? "
                    "And shelves so I don't have to drill too much. I'm open to a small table, "
                    "but we have a toddler, and placing something on a table that's "
                    "low sounds risky."
                ),
                search_attrs=[
                    "Queries address adhesive or low-drill mounting approaches",
                    "Queries consider toddler safety and avoid low-surface assumptions",
                    (
                        "Queries look for shelves or higher placement surfaces rather "
                        "than only low tables"
                    ),
                ],
                forbidden_bundle_attrs=[
                    "A low table or unsupported workaround that ignores the toddler constraint",
                ],
                fixture_name="unsupported_no_match",
                source_thread_id="agent_search-286fe4b8",
                forbid_bundle_call=True,
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
