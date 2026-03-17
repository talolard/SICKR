"""Search-planning eval cases that only judge `run_search_graph` behavior."""

from __future__ import annotations

from pydantic_evals import Case

from evals.search.datasets.common import build_case
from evals.search.types import SearchEvalInput


def build_query_planning_cases() -> list[Case[SearchEvalInput, str, None]]:
    """Return search-only cases that do not rely on seeded bundle fixtures."""

    return [
        build_case(
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
        build_case(
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
        build_case(
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
        build_case(
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
        build_case(
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
    ]


__all__ = ["build_query_planning_cases"]
