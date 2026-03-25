"""Validate the public deploy paths the UI needs on first page load."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import httpx

_HTTP_OK = 200


@dataclass(frozen=True, slots=True)
class EndpointCheck:
    """One public endpoint check with the minimum contract assertions."""

    path: str
    expected_status: int = 200


def _request(client: httpx.Client, base_url: str, check: EndpointCheck) -> httpx.Response:
    return client.get(
        f"{base_url.rstrip('/')}{check.path}",
        headers={"accept": "application/json", "cache-control": "no-store"},
    )


def _assert_health_payload(response: httpx.Response) -> None:
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("status") not in {"ok", "ready"}:
        msg = f"Unexpected /api/health payload: {payload!r}"
        raise AssertionError(msg)


def _assert_agents_payload(response: httpx.Response) -> str:
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("agents"), list):
        msg = f"Unexpected /api/agents payload: {payload!r}"
        raise TypeError(msg)
    agents = payload["agents"]
    if not agents:
        msg = "Expected at least one registered agent from /api/agents."
        raise AssertionError(msg)
    first = agents[0]
    if not isinstance(first, dict):
        msg = f"Expected agent entry object, found {first!r}."
        raise TypeError(msg)
    name = first.get("name")
    if not isinstance(name, str) or not name:
        msg = f"Expected first agent name, found {first!r}."
        raise AssertionError(msg)
    return name


def _assert_metadata_payload(response: httpx.Response, expected_agent: str) -> None:
    payload = response.json()
    if not isinstance(payload, dict):
        msg = f"Unexpected metadata payload: {payload!r}"
        raise TypeError(msg)
    name = payload.get("name")
    if name != expected_agent:
        msg = f"Expected metadata for {expected_agent!r}, found {name!r}."
        raise AssertionError(msg)


def main() -> int:
    """Exit non-zero when the public deploy path is not healthy enough for UI boot."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        required=True,
        help="Public app base URL, for example https://designagent.talperry.com",
    )
    args = parser.parse_args()

    timeout = httpx.Timeout(connect=5.0, read=20.0, write=20.0, pool=None)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        health_response = _request(client, args.base_url, EndpointCheck(path="/api/health"))
        if health_response.status_code != _HTTP_OK:
            msg = f"/api/health returned {health_response.status_code}."
            raise AssertionError(msg)
        _assert_health_payload(health_response)

        agents_response = _request(client, args.base_url, EndpointCheck(path="/api/agents"))
        if agents_response.status_code != _HTTP_OK:
            msg = f"/api/agents returned {agents_response.status_code}."
            raise AssertionError(msg)
        first_agent = _assert_agents_payload(agents_response)

        metadata_response = _request(
            client,
            args.base_url,
            EndpointCheck(path=f"/api/agents/{first_agent}/metadata"),
        )
        if metadata_response.status_code != _HTTP_OK:
            msg = f"/api/agents/{first_agent}/metadata returned {metadata_response.status_code}."
            raise AssertionError(msg)
        _assert_metadata_payload(metadata_response, first_agent)

    print(f"Validated public agent routes on {args.base_url}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
