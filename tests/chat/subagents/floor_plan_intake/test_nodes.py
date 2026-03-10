from __future__ import annotations

from ikea_agent.chat.subagents.floor_plan_intake.nodes import (
    _infer_room_type,
    _is_finish_signal,
    _orientation_prompt,
    _parse_dimensions_cm,
    _parse_height_cm,
    _wants_render_now,
)


def test_parse_dimensions_cm_from_plain_text() -> None:
    assert _parse_dimensions_cm("I have a 300 by 400 room") == (300.0, 400.0)


def test_parse_height_cm_from_text() -> None:
    assert _parse_height_cm("ceiling is 265 cm") == 265.0


def test_infer_room_type_prefers_specific_match() -> None:
    assert _infer_room_type("This is my kitchen", "other") == "kitchen"


def test_infer_room_type_recognizes_living_room_with_common_typo() -> None:
    assert _infer_room_type("I want to redesign my libing room", "other") == "living_room"


def test_infer_room_type_does_not_switch_living_room_on_kitchen_table_phrase() -> None:
    text = "There is a kitchen table and L couch in the center."
    assert _infer_room_type(text, "living_room") == "living_room"


def test_orientation_prompt_includes_hallway_specific_questions() -> None:
    prompt = _orientation_prompt("hallway")
    assert "how many doors are on left and right" in prompt


def test_orientation_prompt_includes_living_room_stability_guidance() -> None:
    prompt = _orientation_prompt("living_room")
    assert "should not change room type" in prompt


def test_orientation_prompt_includes_bedroom_movable_furniture_guidance() -> None:
    prompt = _orientation_prompt("bedroom")
    assert "only call out bed details now if the bed is fixed/mounted" in prompt


def test_render_now_signals_match_corrections_and_move_on() -> None:
    assert _wants_render_now("let's move on")
    assert _wants_render_now("please try again with correction")


def test_finish_signals_match_all_exit_phrases() -> None:
    assert _is_finish_signal("that's perfect")
    assert _is_finish_signal("that's close enough")
    assert _is_finish_signal("let's give up")
