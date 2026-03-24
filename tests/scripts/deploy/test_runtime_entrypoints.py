from __future__ import annotations

import httpx
from scripts.deploy.prove_agui_streaming import prove_agui_stream
from scripts.deploy.wait_for_http_ready import (
    HealthProbeResult,
    probe_http_readiness,
    wait_for_ready,
)


def test_probe_http_readiness_accepts_ok_json_payload() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"status": "ok", "checks": {}})
    )
    client = httpx.Client(transport=transport)

    result = probe_http_readiness("http://testserver/api/health/ready", client=client)

    assert result.ready is True
    assert result.status_code == 200


def test_wait_for_ready_retries_until_probe_succeeds() -> None:
    attempts = iter(
        [
            HealthProbeResult(ready=False, detail="still waking"),
            HealthProbeResult(ready=False, detail="still waking"),
            HealthProbeResult(ready=True, detail="ready"),
        ]
    )
    current_time = 0.0

    def _probe() -> HealthProbeResult:
        return next(attempts)

    def _monotonic() -> float:
        nonlocal current_time
        value = current_time
        current_time += 1.0
        return value

    result = wait_for_ready(
        _probe,
        timeout_seconds=10.0,
        sleep=lambda _seconds: None,
        monotonic=_monotonic,
    )

    assert result.status == "ok"
    assert result.attempts == 3
    assert result.last_probe.detail == "ready"


def test_wait_for_ready_times_out_when_probe_never_succeeds() -> None:
    current_time = 0.0

    def _probe() -> HealthProbeResult:
        return HealthProbeResult(ready=False, detail="still not ready")

    def _monotonic() -> float:
        nonlocal current_time
        value = current_time
        current_time += 1.0
        return value

    result = wait_for_ready(
        _probe,
        timeout_seconds=2.0,
        sleep=lambda _seconds: None,
        monotonic=_monotonic,
    )

    assert result.status == "timeout"
    assert result.last_probe.detail == "still not ready"


def test_prove_agui_stream_accepts_event_stream_response() -> None:
    event_stream_body = b'event: message\ndata: {"status":"ok"}\n\n'
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=event_stream_body,
        )
    )
    client = httpx.Client(transport=transport)

    result = prove_agui_stream(
        "http://testserver/ag-ui/agents/search",
        payload={"messages": []},
        client=client,
    )

    assert result.status == "ok"
    assert result.observed_chunks == 1
    assert result.first_chunk_preview is not None


def test_prove_agui_stream_rejects_non_streaming_response() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"status": "ok"},
        )
    )
    client = httpx.Client(transport=transport)

    result = prove_agui_stream(
        "http://testserver/ag-ui/agents/search",
        payload={"messages": []},
        client=client,
    )

    assert result.status == "failed"
    assert result.content_type == "application/json"
