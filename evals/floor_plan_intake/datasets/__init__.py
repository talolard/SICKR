"""Floor-plan intake eval dataset package.

Quick run:

```bash
uv run python -m evals.floor_plan_intake
```

Initial cases focus on the highest-leverage floor-plan contracts:

- brief, orientation-first opening replies
- render follow-through once the user says to move on to a draft

The first authoring pass is grounded in prompt review plus live traces:

- `019d01cf54467b5db80da0685a45c7da`: real opening reply for a short living-room prompt
- `019d01d1da6dcb6d07cd57e8cc8c234f`: invalid `render_floor_plan` call missing `scene_level`
- `019d01d3d55c952fd91297f6bf307690`: corrected render call that produced revision 2
"""

from __future__ import annotations

from pydantic_evals import Dataset
from pydantic_evals.evaluators import LLMJudge

from evals.floor_plan_intake.datasets.brief_openers import build_brief_opener_cases
from evals.floor_plan_intake.datasets.common import JUDGE_MODEL, OPENING_RUBRIC
from evals.floor_plan_intake.datasets.draft_progression import (
    build_draft_progression_cases,
)
from evals.floor_plan_intake.evaluators import (
    FinalOutputContractEvaluator,
    RenderToolCallContractEvaluator,
    ReplyQuestionCountEvaluator,
    ReplyWordCountEvaluator,
)
from evals.floor_plan_intake.types import FloorPlanIntakeEvalInput


def build_floor_plan_intake_eval_dataset() -> Dataset[FloorPlanIntakeEvalInput, str, None]:
    """Build the authoritative floor-plan intake eval dataset."""

    return Dataset(
        name="floor_plan_intake_agent_quality",
        cases=[
            *build_brief_opener_cases(),
            *build_draft_progression_cases(),
        ],
        evaluators=[
            LLMJudge(
                rubric=OPENING_RUBRIC,
                model=JUDGE_MODEL,
                include_input=True,
                score=False,
                assertion={
                    "evaluation_name": "floor_plan_response_quality",
                    "include_reason": True,
                },
            ),
            FinalOutputContractEvaluator(),
            ReplyWordCountEvaluator(),
            ReplyQuestionCountEvaluator(),
            RenderToolCallContractEvaluator(),
        ],
    )


__all__ = ["build_floor_plan_intake_eval_dataset"]
