"""Bundle-stage search eval cases that rely on seeded retrieval fixtures."""

from __future__ import annotations

from pydantic_evals import Case

from evals.search.datasets.common import build_case
from evals.search.types import SearchEvalInput


def build_bundle_follow_through_cases() -> list[Case[SearchEvalInput, str, None]]:
    """Return cases that judge how retrieval results turn into bundle proposals."""

    return [
        build_case(
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
        build_case(
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
        build_case(
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
        build_case(
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
    ]


__all__ = ["build_bundle_follow_through_cases"]
