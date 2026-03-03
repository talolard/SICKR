from __future__ import annotations

from tal_maria_ikea.ingest.index import _compute_backoff_seconds, _extract_retry_delay_seconds


def test_extract_retry_delay_seconds_from_direct_message() -> None:
    message = "Please retry in 34.242954s."
    assert _extract_retry_delay_seconds(message) == 34.242954


def test_extract_retry_delay_seconds_from_retry_info_detail() -> None:
    message = "'retryDelay': '33s'"
    assert _extract_retry_delay_seconds(message) == 33.0


def test_compute_backoff_seconds_uses_retry_hint_floor() -> None:
    backoff = _compute_backoff_seconds(
        attempt=1,
        retry_hint=33.0,
        base_seconds=2.0,
        max_seconds=90.0,
        jitter_seconds=0.0,
    )
    assert backoff == 33.0


def test_compute_backoff_seconds_exponential_without_hint() -> None:
    backoff = _compute_backoff_seconds(
        attempt=3,
        retry_hint=None,
        base_seconds=2.0,
        max_seconds=90.0,
        jitter_seconds=0.0,
    )
    assert backoff == 8.0
