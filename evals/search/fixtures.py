"""Seeded retrieval fixtures for search-agent eval cases.

These fixtures are intentionally scenario-driven. Some cases only need seeded retrieval
results so the real agent can continue from `run_search_graph` into `propose_bundle`.
Others, such as thread-derived bundle realism checks, need a narrow continuation slice:
real prior conversation context plus a grounded search batch already in history.

Read this module as "bundle-stage eval inputs", not as a fake catalog. Add only the
products and prior-turn context required to exercise the behavior being judged.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from ikea_agent.shared.types import (
    SearchBatchToolResult,
    SearchQueryToolResult,
    ShortRetrievalResult,
)


def _result(
    *,
    product_id: str,
    product_name: str,
    description_text: str,
    product_type: str = "Furniture",
    main_category: str = "general",
    sub_category: str = "general",
    width_cm: float | None = None,
    depth_cm: float | None = None,
    height_cm: float | None = None,
    price_eur: float | None = None,
    url: str | None = None,
    display_title: str | None = None,
    image_urls: tuple[str, ...] = (),
) -> ShortRetrievalResult:
    return ShortRetrievalResult(
        product_id=product_id,
        product_name=product_name,
        display_title=display_title,
        url=url,
        product_type=product_type,
        description_text=description_text,
        main_category=main_category,
        sub_category=sub_category,
        width_cm=width_cm,
        depth_cm=depth_cm,
        height_cm=height_cm,
        price_eur=price_eur,
        image_urls=image_urls,
    )


def _query_result(
    *,
    query_id: str,
    semantic_query: str,
    results: tuple[ShortRetrievalResult, ...],
    total_candidates: int = 20,
) -> SearchQueryToolResult:
    return SearchQueryToolResult(
        query_id=query_id,
        semantic_query=semantic_query,
        results=list(results),
        total_candidates=total_candidates,
        returned_count=len(results),
    )


def _message_with_user(text: str, *, run_id: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=text)], run_id=run_id)


def _message_with_text(text: str, *, run_id: str) -> ModelResponse:
    return ModelResponse(
        parts=[TextPart(content=text)],
        model_name="eval-fixture",
        run_id=run_id,
    )


def _message_with_tool_call(
    *,
    tool_name: str,
    args: dict[str, object],
    tool_call_id: str,
    run_id: str,
) -> ModelResponse:
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name=tool_name,
                args=args,
                tool_call_id=tool_call_id,
            )
        ],
        model_name="eval-fixture",
        run_id=run_id,
    )


def _message_with_tool_return(
    *,
    tool_name: str,
    content: dict[str, object],
    tool_call_id: str,
    run_id: str,
) -> ModelRequest:
    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name=tool_name,
                content=content,
                tool_call_id=tool_call_id,
            )
        ],
        run_id=run_id,
    )


@dataclass(frozen=True, slots=True)
class SearchEvalQueryOverride:
    """Specific seeded results for queries that mention certain terms."""

    query_terms: tuple[str, ...]
    results: tuple[ShortRetrievalResult, ...]

    def matches(self, semantic_query: str) -> bool:
        """Return True when the semantic query should use this override result set."""

        normalized_query = semantic_query.lower()
        return any(term.lower() in normalized_query for term in self.query_terms)


@dataclass(frozen=True, slots=True)
class SearchEvalFixture:
    """Fixture-backed retrieval and optional continuation history for one scenario."""

    name: str
    description: str
    default_results: tuple[ShortRetrievalResult, ...] = ()
    query_overrides: tuple[SearchEvalQueryOverride, ...] = ()
    message_history: tuple[ModelMessage, ...] = ()
    grounded_batches: tuple[SearchBatchToolResult, ...] = ()

    def resolve_results(self, semantic_query: str) -> list[ShortRetrievalResult]:
        """Return seeded results for one semantic query."""

        for override in self.query_overrides:
            if override.matches(semantic_query):
                return list(override.results)
        return list(self.default_results)


_STEUERBERATER_DESK = _result(
    product_id="49513956-DE",
    product_name="MITTZON",
    display_title="MITTZON Desk Walnut Veneer Black S49513956",
    description_text=(
        "MITTZON desk: brown wooden top, black metal base, adjustable height, modern office design."
    ),
    product_type="Furniture",
    main_category="office",
    sub_category="desk",
    price_eur=249.0,
    url="https://www.ikea.com/de/en/p/mittzon-desk-walnut-veneer-black-s49513956/",
)
_STEUERBERATER_EXECUTIVE_CHAIR = _result(
    product_id="70367458-DE",
    product_name="ALEFJÄLL",
    display_title="ALEFJÄLL Alefjaell Office Chair Glose Black",
    description_text=(
        "The ALEFJÄLL office chair in black leather a high back, adjustable lumbar "
        "support, padded armrests, and a five-wheel base for mobility and comfort."
    ),
    product_type="Furniture",
    main_category="office",
    sub_category="office_chair",
    price_eur=349.0,
    url="https://www.ikea.com/de/en/p/alefjaell-office-chair-glose-black-70367458/",
)
_STEUERBERATER_BROR_STORAGE = _result(
    product_id="9423217-DE",
    product_name="BROR",
    display_title="BROR Shelving Unit W Cabinets Drawers Black S09423217",
    description_text=(
        "A black BROR storage system, featuring a tall cabinet and a workbench with "
        "drawers. Both pieces are made of metal with a sleek, modern design."
    ),
    product_type="Storage",
    main_category="storage",
    sub_category="shelving_unit",
    price_eur=428.0,
    url="https://www.ikea.com/de/en/p/bror-shelving-unit-w-cabinets-drawers-black-s09423217/",
)
_STEUERBERATER_CONFERENCE_TABLE = _result(
    product_id="59532817-DE",
    product_name="MITTZON",
    display_title="MITTZON Conference Table OAK Veneer Black S59532817",
    description_text=(
        "MITTZON: modern, black metal conference table with square oak top, standing height."
    ),
    product_type="Furniture",
    main_category="office",
    sub_category="conference_table",
    price_eur=259.0,
    url="https://www.ikea.com/de/en/p/mittzon-conference-table-oak-veneer-black-s59532817/",
)
_STEUERBERATER_CONFERENCE_CHAIR = _result(
    product_id="19513123-DE",
    product_name="TOSSBERG / LÅNGFJÄLL",
    display_title=(
        "TOSSBERG / LÅNGFJÄLL Tossberg Langfjaell Conference Chair "
        "Gunnared Dark Grey Black S19513123"
    ),
    description_text=(
        "TOSSBERG chair: grey, soft fabric, padded, black swivel base, five wheels, "
        "ergonomic design."
    ),
    product_type="Furniture",
    main_category="office",
    sub_category="conference_chair",
    price_eur=199.0,
    url="https://www.ikea.com/de/en/p/tossberg-langfjaell-conference-chair-gunnared-dark-grey-black-s19513123/",
)
_STEUERBERATER_IDASEN_CABINET = _result(
    product_id="50496381-DE",
    product_name="IDÅSEN",
    display_title="IDÅSEN Idasen Cabinet With Doors AND Drawers Dark Grey",
    description_text=(
        "This is an IDÅSEN dark grey metal cabinet with 2 drawers and 2 doors, "
        "featuring a modern and minimalist design for storage."
    ),
    product_type="Storage",
    main_category="storage",
    sub_category="cabinet",
    price_eur=349.0,
    url="https://www.ikea.com/de/en/p/idasen-cabinet-with-doors-and-drawers-dark-grey-50496381/",
)
_STEUERBERATER_FLOOR_LAMP = _result(
    product_id="215307-DE",
    product_name="HEKTAR",
    display_title="HEKTAR Floor Lamp Dark Grey",
    description_text=(
        "A black HEKTAR floor lamp. It has an industrial design with an adjustable, "
        "oversized metal shade."
    ),
    product_type="Lighting",
    main_category="lighting",
    sub_category="floor_lamp",
    price_eur=59.99,
    url="https://www.ikea.com/de/en/p/hektar-floor-lamp-dark-grey-00215307/",
)

_STEUERBERATER_PRODUCT_SET: tuple[ShortRetrievalResult, ...] = (
    _STEUERBERATER_DESK,
    _STEUERBERATER_EXECUTIVE_CHAIR,
    _STEUERBERATER_BROR_STORAGE,
    _STEUERBERATER_CONFERENCE_TABLE,
    _STEUERBERATER_CONFERENCE_CHAIR,
    _STEUERBERATER_IDASEN_CABINET,
    _STEUERBERATER_FLOOR_LAMP,
)

_STEUERBERATER_REGROUNDING_BATCH = SearchBatchToolResult(
    queries=[
        _query_result(
            query_id="steuerberater-desk",
            semantic_query="MITTZON desk walnut black",
            results=(_STEUERBERATER_DESK,),
        ),
        _query_result(
            query_id="steuerberater-chair",
            semantic_query="ALEFJÄLL office chair black leather",
            results=(_STEUERBERATER_EXECUTIVE_CHAIR,),
        ),
        _query_result(
            query_id="steuerberater-bror",
            semantic_query="BROR shelving unit with cabinets drawers black",
            results=(_STEUERBERATER_BROR_STORAGE,),
        ),
        _query_result(
            query_id="steuerberater-table",
            semantic_query="MITTZON conference table oak veneer black",
            results=(_STEUERBERATER_CONFERENCE_TABLE,),
        ),
        _query_result(
            query_id="steuerberater-conference-chair",
            semantic_query="TOSSBERG LÅNGFJÄLL conference chair",
            results=(_STEUERBERATER_CONFERENCE_CHAIR,),
        ),
        _query_result(
            query_id="steuerberater-cabinet",
            semantic_query="IDÅSEN cabinet with doors and drawers dark grey",
            results=(_STEUERBERATER_IDASEN_CABINET,),
        ),
        _query_result(
            query_id="steuerberater-lamp",
            semantic_query="HEKTAR floor lamp dark grey",
            results=(_STEUERBERATER_FLOOR_LAMP,),
        ),
    ]
)
_STEUERBERATER_REGROUNDING_TOOL_ARGS: dict[str, object] = {
    "queries": [
        {
            "query_id": "steuerberater-desk",
            "semantic_query": "MITTZON desk walnut black",
            "purpose": "Re-grounding executive desk for bundle.",
        },
        {
            "query_id": "steuerberater-chair",
            "semantic_query": "ALEFJÄLL office chair black leather",
            "purpose": "Re-grounding command chair for bundle.",
        },
        {
            "query_id": "steuerberater-bror",
            "semantic_query": "BROR shelving unit with cabinets drawers black",
            "purpose": "Re-grounding archive shelving for bundle.",
        },
        {
            "query_id": "steuerberater-table",
            "semantic_query": "MITTZON conference table oak veneer black",
            "purpose": "Re-grounding conference table for bundle.",
        },
        {
            "query_id": "steuerberater-conference-chair",
            "semantic_query": "TOSSBERG LÅNGFJÄLL conference chair",
            "purpose": "Re-grounding conference chairs for bundle.",
        },
        {
            "query_id": "steuerberater-cabinet",
            "semantic_query": "IDÅSEN cabinet with doors and drawers dark grey",
            "purpose": "Re-grounding lockable cabinets for bundle.",
        },
        {
            "query_id": "steuerberater-lamp",
            "semantic_query": "HEKTAR floor lamp dark grey",
            "purpose": "Re-grounding floor lamp for bundle.",
        },
    ]
}
_STEUERBERATER_INITIAL_PROMPT = (
    "My friend Anna is a bad ass former consultant who drinks the bloog of her enemies "
    "as a protien shake. She is brcoming a german Steuerberater with Hans and Klaus and "
    "wants to decorate to capture all that paperwork, her personality and the germanness "
    "of hans and klaus the Steuerberater. Budget of 15000 euros for a single 8 by 6 meter room"
)
_STEUERBERATER_CONCEPT_RESPONSE = """\
This is a massive space (48m²) that demands a commanding presence. To capture the "badass
former consultant" energy and the rigorous requirements of a German Steuerberater office,
we will build a high-contrast, industrial-executive command center.

Proposed "Executive Precision" bundle direction:
- MITTZON Executive Desk (Walnut/Black): 1
- ALEFJÄLL Leather Executive Chair (Black): 1
- BROR Storage System (Cabinets & Shelving): 4+
- MITTZON Conference Table (Round/Oak): 1
- ALEFJÄLL or equivalent consultation chairs: 4
- HEKTAR Industrial Floor Lamps: 2

Would you like me to refine this into a formal bundle for you, or should we look into
specific organizational accessories to complete the Ordnung of the archive?
"""
_STEUERBERATER_CONTINUATION_HISTORY: tuple[ModelMessage, ...] = (
    _message_with_user(_STEUERBERATER_INITIAL_PROMPT, run_id="fixture-search-1"),
    _message_with_text(_STEUERBERATER_CONCEPT_RESPONSE, run_id="fixture-search-1"),
    _message_with_user("Yes", run_id="fixture-search-2"),
    _message_with_tool_call(
        tool_name="run_search_graph",
        args=_STEUERBERATER_REGROUNDING_TOOL_ARGS,
        tool_call_id="tool-call-steuerberater-reground",
        run_id="fixture-search-2",
    ),
    _message_with_tool_return(
        tool_name="run_search_graph",
        content=asdict(_STEUERBERATER_REGROUNDING_BATCH),
        tool_call_id="tool-call-steuerberater-reground",
        run_id="fixture-search-2",
    ),
)


SEARCH_EVAL_FIXTURES: dict[str, SearchEvalFixture] = {
    "gallery_wall_bundle_seed": SearchEvalFixture(
        name="gallery_wall_bundle_seed",
        description=(
            "Fixture distilled from the existing rental-gallery-wall search scenario so "
            "the eval can exercise `propose_bundle` after retrieval."
        ),
        default_results=(
            _result(
                product_id="gallery-frame-1",
                product_name="LUSTIGT frame set",
                description_text="Photo frame set for a mixed gallery wall display.",
                product_type="Decoration",
                main_category="decoration",
                sub_category="frames",
                price_eur=29.99,
            ),
            _result(
                product_id="gallery-shelf-1",
                product_name="MOSSLANDA picture ledge",
                description_text="Shallow wall ledge suited to photos and small decor.",
                product_type="Storage",
                main_category="storage",
                sub_category="wall_shelf",
                width_cm=55.0,
                depth_cm=12.0,
                height_cm=7.0,
                price_eur=14.99,
            ),
            _result(
                product_id="gallery-clock-1",
                product_name="PLUGGIS wall clock",
                description_text="Compact decorative wall clock to break up a photo display.",
                product_type="Decoration",
                main_category="decoration",
                sub_category="clock",
                price_eur=19.99,
            ),
            _result(
                product_id="gallery-adhesive-1",
                product_name="Damage-free mounting strips",
                description_text="High-strength adhesive mounting strips for renter-safe installs.",
                product_type="Accessories",
                main_category="organizers",
                sub_category="mounting",
                price_eur=7.99,
            ),
        ),
    ),
    "hallway_complementary_seed": SearchEvalFixture(
        name="hallway_complementary_seed",
        description=(
            "Fixture grounded in thread agent_search-286fe4b8, with portable lights and "
            "supporting products such as floating shelves, adhesive mounts, and a narrow "
            "console table."
        ),
        default_results=(
            _result(
                product_id="hall-lamp-1",
                product_name="LÄNSPORT portable lamp",
                description_text="Battery-powered portable lamp for shelf or ledge placement.",
                product_type="Lighting",
                main_category="lighting",
                sub_category="portable_lamp",
                price_eur=17.99,
            ),
            _result(
                product_id="hall-lamp-2",
                product_name="NÖDMAST portable lamp",
                description_text="Portable accent lamp that works without wall wiring.",
                product_type="Lighting",
                main_category="lighting",
                sub_category="portable_lamp",
                price_eur=14.99,
            ),
            _result(
                product_id="hall-shelf-1",
                product_name="BERGSHULT floating shelf",
                description_text="Narrow floating shelf suitable for a hallway wall.",
                product_type="Storage",
                main_category="storage",
                sub_category="wall_shelf",
                width_cm=80.0,
                depth_cm=20.0,
                height_cm=3.0,
                price_eur=24.99,
            ),
            _result(
                product_id="hall-console-1",
                product_name="TORNBY narrow console table",
                description_text=(
                    "Slim hallway console table for surfaces where drilling is not ideal."
                ),
                product_type="Furniture",
                main_category="living_room",
                sub_category="console_table",
                width_cm=90.0,
                depth_cm=24.0,
                height_cm=75.0,
                price_eur=59.99,
            ),
            _result(
                product_id="hall-adhesive-1",
                product_name="Damage-free adhesive strips",
                description_text="Adhesive mounting strips for lighter wall accessories.",
                product_type="Accessories",
                main_category="organizers",
                sub_category="mounting",
                price_eur=8.99,
            ),
        ),
    ),
    "unsupported_no_match": SearchEvalFixture(
        name="unsupported_no_match",
        description=(
            "Deliberately empty results for requests that the current catalog cannot satisfy, "
            "used to assert that the agent does not fabricate a bundle."
        ),
    ),
    "steuerberater_bundle_continuation": SearchEvalFixture(
        name="steuerberater_bundle_continuation",
        description=(
            "Thread-derived continuation fixture from agent_search-fe0d9f2d. The prior turn "
            "already converged on an executive-office direction, the user said yes, and the "
            "agent re-grounded the exact products before deciding whether to bundle."
        ),
        default_results=_STEUERBERATER_PRODUCT_SET,
        query_overrides=(
            SearchEvalQueryOverride(
                query_terms=("MITTZON desk walnut black",),
                results=(_STEUERBERATER_DESK,),
            ),
            SearchEvalQueryOverride(
                query_terms=("ALEFJÄLL office chair black leather",),
                results=(_STEUERBERATER_EXECUTIVE_CHAIR,),
            ),
            SearchEvalQueryOverride(
                query_terms=("BROR shelving unit with cabinets drawers black",),
                results=(_STEUERBERATER_BROR_STORAGE,),
            ),
            SearchEvalQueryOverride(
                query_terms=("MITTZON conference table oak veneer black",),
                results=(_STEUERBERATER_CONFERENCE_TABLE,),
            ),
            SearchEvalQueryOverride(
                query_terms=("TOSSBERG LÅNGFJÄLL conference chair",),
                results=(_STEUERBERATER_CONFERENCE_CHAIR,),
            ),
            SearchEvalQueryOverride(
                query_terms=("IDÅSEN cabinet with doors and drawers dark grey",),
                results=(_STEUERBERATER_IDASEN_CABINET,),
            ),
            SearchEvalQueryOverride(
                query_terms=("HEKTAR floor lamp dark grey",),
                results=(_STEUERBERATER_FLOOR_LAMP,),
            ),
        ),
        message_history=_STEUERBERATER_CONTINUATION_HISTORY,
        grounded_batches=(_STEUERBERATER_REGROUNDING_BATCH,),
    ),
}
