"""Check that one AG-UI endpoint responds as SSE and emits an early event chunk."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

import httpx

_HTTP_OK = 200


@dataclass(frozen=True, slots=True)
class AgUiStreamingProof:
    """Compact outcome from a narrow AG-UI SSE response-surface check."""

    status: Literal["ok", "failed"]
    detail: str
    status_code: int | None
    content_type: str | None
    first_chunk_preview: str | None
    first_chunk_seconds: float | None
    observed_chunks: int


def _default_ag_ui_url() -> str:
    configured = os.getenv("PY_AG_UI_URL", "http://127.0.0.1:8000/ag-ui/")
    if "/agents/" in configured:
        return configured
    base = configured if configured.endswith("/") else f"{configured}/"
    return urljoin(base, "agents/search")


def _default_payload(*, message: str, run_id: str, thread_id: str) -> dict[str, object]:
    return {
        "threadId": thread_id,
        "runId": run_id,
        "state": {},
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": message,
            }
        ],
    }


def _load_payload(
    *,
    payload_file: Path | None,
    message: str,
    run_id: str,
    thread_id: str,
) -> dict[str, object]:
    if payload_file is None:
        return _default_payload(message=message, run_id=run_id, thread_id=thread_id)
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected JSON object payload in {payload_file}."
        raise TypeError(msg)
    return payload


def prove_agui_stream(
    url: str,
    *,
    payload: dict[str, object],
    client: httpx.Client | None = None,
    first_chunk_timeout_seconds: float = 15.0,
) -> AgUiStreamingProof:
    """Post one AG-UI request and verify that SSE response framing begins promptly."""

    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=httpx.Timeout(
            connect=10.0,
            read=first_chunk_timeout_seconds,
            write=10.0,
            pool=None,
        )
    )
    started_at = time.monotonic()
    try:
        with http_client.stream(
            "POST",
            url,
            json=payload,
            headers={
                "accept": "text/event-stream",
                "cache-control": "no-store",
            },
        ) as response:
            content_type = response.headers.get("content-type")
            if response.status_code != _HTTP_OK:
                body = response.read().decode("utf-8", errors="replace")
                return AgUiStreamingProof(
                    status="failed",
                    detail=f"Endpoint returned HTTP {response.status_code}: {body[:200]}",
                    status_code=response.status_code,
                    content_type=content_type,
                    first_chunk_preview=None,
                    first_chunk_seconds=None,
                    observed_chunks=0,
                )
            if not content_type or not content_type.startswith("text/event-stream"):
                return AgUiStreamingProof(
                    status="failed",
                    detail=f"Expected text/event-stream but received {content_type!r}.",
                    status_code=response.status_code,
                    content_type=content_type,
                    first_chunk_preview=None,
                    first_chunk_seconds=None,
                    observed_chunks=0,
                )

            observed_chunks = 0
            for chunk in response.iter_text():
                if not chunk.strip():
                    continue
                observed_chunks += 1
                return AgUiStreamingProof(
                    status="ok",
                    detail=(
                        "Observed an SSE response with one non-empty AG-UI chunk. "
                        "This checks SSE response shape and first-event delivery only; "
                        "it does not prove unbuffered progressive streaming "
                        "through the public edge."
                    ),
                    status_code=response.status_code,
                    content_type=content_type,
                    first_chunk_preview=chunk[:200],
                    first_chunk_seconds=round(time.monotonic() - started_at, 3),
                    observed_chunks=observed_chunks,
                )
            return AgUiStreamingProof(
                status="failed",
                detail="Response completed without any non-empty streamed chunks.",
                status_code=response.status_code,
                content_type=content_type,
                first_chunk_preview=None,
                first_chunk_seconds=None,
                observed_chunks=observed_chunks,
            )
    except httpx.HTTPError as exc:
        return AgUiStreamingProof(
            status="failed",
            detail=str(exc),
            status_code=None,
            content_type=None,
            first_chunk_preview=None,
            first_chunk_seconds=None,
            observed_chunks=0,
        )
    finally:
        if owns_client:
            http_client.close()


def main() -> int:
    """Run the deploy-oriented AG-UI SSE response-surface check."""

    parser = argparse.ArgumentParser(
        description=(
            "Check that an AG-UI endpoint returns text/event-stream and emits one "
            "non-empty chunk before the first-event timeout. "
            "This is not a full proof of edge-safe progressive streaming."
        )
    )
    parser.add_argument(
        "--url",
        default=_default_ag_ui_url(),
        help="AG-UI agent endpoint URL to test.",
    )
    parser.add_argument(
        "--payload-file",
        type=Path,
        default=None,
        help="Optional JSON payload file to POST instead of the generated default payload.",
    )
    parser.add_argument(
        "--message",
        default="Deploy SSE response-surface check request.",
        help="User message used when building the default AG-UI payload.",
    )
    parser.add_argument("--thread-id", default="deploy-proof-thread")
    parser.add_argument("--run-id", default="deploy-proof-run")
    parser.add_argument(
        "--first-chunk-timeout-seconds",
        type=float,
        default=15.0,
        help="Socket read timeout while waiting for the first streamed chunk.",
    )
    args = parser.parse_args()

    payload = _load_payload(
        payload_file=args.payload_file,
        message=args.message,
        run_id=args.run_id,
        thread_id=args.thread_id,
    )
    result = prove_agui_stream(
        args.url,
        payload=payload,
        first_chunk_timeout_seconds=args.first_chunk_timeout_seconds,
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
