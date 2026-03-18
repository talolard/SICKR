"""Render follow-through eval cases for floor-plan intake."""

from __future__ import annotations

from pydantic_evals import Case

from evals.floor_plan_intake.datasets.common import build_case
from evals.floor_plan_intake.types import FloorPlanIntakeEvalInput


def build_draft_progression_cases() -> list[Case[FloorPlanIntakeEvalInput, str, None]]:
    """Return cases that judge moving from intake detail into a first draft."""

    return [
        build_case(
            "hallway_move_on_to_first_draft",
            (
                "It's a hallway and let's move on to a first draft. Standing with my back "
                "to the entrance, the room is about 500 cm wide and 400 cm deep. "
                "Use the standard ceiling height if needed. The entrance door is on the "
                "door wall, centered roughly from x 180 to 260 cm, and opens inward. "
                "The far wall has one window from about x 120 to 380 cm. The left wall "
                "and right wall are plain for now."
            ),
            response_attrs=[
                "Frames the output as a draft with assumptions or approximations",
                "Uses the named wall vocabulary consistently",
                "Asks whether the draft looks right or needs corrections",
            ],
            render_attrs=[
                "Calls render_floor_plan with a baseline scene",
                "Represents four perimeter walls, one entrance door, and one far-wall window",
                "Uses the supplied 500 by 400 cm envelope and a default 280 cm height",
                "Includes image bytes so the preview can render inline",
            ],
            max_word_count=200,
            max_question_count=1,
            require_render_call=True,
            source_trace_id="019d01d3d55c952fd91297f6bf307690",
        ),
    ]


__all__ = ["build_draft_progression_cases"]
