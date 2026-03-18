from __future__ import annotations

from evals.floor_plan_intake import build_floor_plan_intake_eval_dataset


def test_build_floor_plan_intake_eval_dataset_collects_all_case_modules() -> None:
    dataset = build_floor_plan_intake_eval_dataset()

    assert [case.name for case in dataset.cases] == [
        "living_room_redesign_brief_opener",
        "hallway_one_line_brief_opener",
        "small_bathroom_no_measurements_brief_opener",
        "hallway_move_on_to_first_draft",
    ]
