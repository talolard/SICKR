"""Floor-plan intake eval package.

Use `uv run python -m evals.floor_plan_intake` to run the live eval harness from the
command line. The assembled dataset is exposed here for programmatic use, while the
case definitions themselves live under `evals.floor_plan_intake.datasets`.
"""

from evals.floor_plan_intake.dataset import build_floor_plan_intake_eval_dataset
from evals.floor_plan_intake.harness import FloorPlanIntakeEvalHarness
from evals.floor_plan_intake.types import (
    FloorPlanIntakeEvalInput,
    FloorPlanIntakeEvalRunCapture,
)

__all__ = [
    "FloorPlanIntakeEvalHarness",
    "FloorPlanIntakeEvalInput",
    "FloorPlanIntakeEvalRunCapture",
    "build_floor_plan_intake_eval_dataset",
]
