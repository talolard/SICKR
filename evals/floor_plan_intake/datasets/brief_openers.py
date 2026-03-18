"""Opening-turn eval cases for concise floor-plan intake behavior."""

from __future__ import annotations

from pydantic_evals import Case

from evals.floor_plan_intake.datasets.common import build_case
from evals.floor_plan_intake.types import FloorPlanIntakeEvalInput


def build_brief_opener_cases() -> list[Case[FloorPlanIntakeEvalInput, str, None]]:
    """Return opening-turn cases focused on concise orientation-first replies."""

    return [
        build_case(
            "living_room_redesign_brief_opener",
            "Hi, I have a living room and I want to work on the redesign",
            response_attrs=[
                "Confirms the living room as the working room type",
                "Defers furniture/layout and keeps focus on room shell",
                "Establishes door wall, left wall, right wall, and far wall",
                "Asks one focused follow-up about openings or fixed features",
            ],
            max_word_count=190,
            max_question_count=1,
            source_trace_id="019d01cf54467b5db80da0685a45c7da",
        ),
        build_case(
            "hallway_one_line_brief_opener",
            "Dark hallway.",
            response_attrs=[
                "Treats hallway as the likely room type or asks to confirm it briefly",
                "Starts with orientation instead of immediately requesting measurements",
                "Asks one focused question about doors, openings, or fixed elements",
                "Keeps the reply practical and low-pressure",
            ],
            max_word_count=130,
            max_question_count=1,
        ),
        build_case(
            "small_bathroom_no_measurements_brief_opener",
            "Small bathroom, no measurements yet.",
            response_attrs=[
                "Keeps bathroom as the room type",
                "Reassures the user that rough estimates are acceptable",
                "Avoids opening with a blunt dimensions-only question",
                "Asks one focused question about visible fixtures or openings",
            ],
            forbidden_response_terms=["What are the dimensions?"],
            max_word_count=150,
            max_question_count=1,
        ),
    ]


__all__ = ["build_brief_opener_cases"]
