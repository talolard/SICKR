from __future__ import annotations

from tal_maria_ikea.eval.generate import _normalize_query_text, _plan_round_requests


def test_plan_round_requests_no_remaining() -> None:
    assert _plan_round_requests(remaining=0, batch_size=25, parallelism=4) == []


def test_plan_round_requests_single_request_partial_batch() -> None:
    assert _plan_round_requests(remaining=7, batch_size=25, parallelism=4) == [7]


def test_plan_round_requests_multiple_requests_with_tail() -> None:
    assert _plan_round_requests(remaining=52, batch_size=25, parallelism=4) == [25, 25, 2]


def test_normalize_query_text_collapses_case_and_whitespace() -> None:
    assert _normalize_query_text("  Small   WHITE  desk  ") == "small white desk"
