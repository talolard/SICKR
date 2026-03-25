"""Poll one HTTP health endpoint until it reports ready or times out."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal

import httpx

_HTTP_OK = 200


@dataclass(frozen=True, slots=True)
class HealthProbeResult:
    """One readiness probe outcome suitable for deploy polling."""

    ready: bool
    detail: str
    status_code: int | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class WaitForReadyResult:
    """Final result from waiting on one readiness endpoint."""

    status: Literal["ok", "timeout"]
    attempts: int
    elapsed_seconds: float
    last_probe: HealthProbeResult


def _parse_json_payload(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def probe_http_readiness(
    url: str,
    *,
    client: httpx.Client | None = None,
) -> HealthProbeResult:
    """Probe one JSON health endpoint and normalize the readiness outcome."""

    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=None)
    )
    try:
        response = http_client.get(
            url,
            headers={
                "accept": "application/json",
                "cache-control": "no-store",
            },
        )
    except httpx.HTTPError as exc:
        return HealthProbeResult(ready=False, detail=str(exc))
    finally:
        if owns_client:
            http_client.close()

    payload = _parse_json_payload(response)
    status_value = payload.get("status") if payload else None
    if response.status_code == _HTTP_OK and status_value in {"ok", "ready"}:
        return HealthProbeResult(
            ready=True,
            detail=f"Endpoint {url} reported {status_value}.",
            payload=payload,
            status_code=response.status_code,
        )

    detail = f"Endpoint {url} returned HTTP {response.status_code}."
    if status_value is not None:
        detail = f"{detail} Reported status={status_value!r}."
    elif payload is None:
        detail = f"{detail} Response was not valid JSON."
    return HealthProbeResult(
        ready=False,
        detail=detail,
        payload=payload,
        status_code=response.status_code,
    )


def wait_for_ready(
    probe: Callable[[], HealthProbeResult],
    *,
    timeout_seconds: float,
    initial_backoff_seconds: float = 1.0,
    max_backoff_seconds: float = 10.0,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> WaitForReadyResult:
    """Retry one readiness probe with backoff until ready or timed out."""

    started_at = monotonic()
    deadline = started_at + timeout_seconds
    attempts = 0
    last_probe = HealthProbeResult(ready=False, detail="No readiness probes were attempted yet.")
    backoff_seconds = initial_backoff_seconds

    while True:
        attempts += 1
        last_probe = probe()
        if last_probe.ready:
            return WaitForReadyResult(
                status="ok",
                attempts=attempts,
                elapsed_seconds=round(monotonic() - started_at, 3),
                last_probe=last_probe,
            )

        now = monotonic()
        if now >= deadline:
            return WaitForReadyResult(
                status="timeout",
                attempts=attempts,
                elapsed_seconds=round(now - started_at, 3),
                last_probe=last_probe,
            )

        sleep(min(backoff_seconds, deadline - now))
        backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)


def main() -> int:
    """Wait for a configured HTTP readiness endpoint."""

    parser = argparse.ArgumentParser(description="Wait for an HTTP readiness endpoint.")
    parser.add_argument("--url", required=True, help="Health/readiness endpoint to poll.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=180.0,
        help="Maximum total time to wait before failing.",
    )
    parser.add_argument(
        "--initial-backoff-seconds",
        type=float,
        default=1.0,
        help="Initial backoff delay between readiness attempts.",
    )
    parser.add_argument(
        "--max-backoff-seconds",
        type=float,
        default=10.0,
        help="Maximum backoff delay between readiness attempts.",
    )
    args = parser.parse_args()

    result = wait_for_ready(
        lambda: probe_http_readiness(args.url),
        timeout_seconds=args.timeout_seconds,
        initial_backoff_seconds=args.initial_backoff_seconds,
        max_backoff_seconds=args.max_backoff_seconds,
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
