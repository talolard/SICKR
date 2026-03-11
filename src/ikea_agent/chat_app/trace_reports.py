"""Trace report bundle persistence helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ikea_agent.persistence.run_history_repository import ThreadRunHistoryEntry

REDACTED_VALUE = "[REDACTED]"
_MAX_SLUG_LENGTH = 80

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:password|passwd|secret|token|api[-_]?key|authorization|cookie|session|bearer)",
    re.IGNORECASE,
)

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class TraceReportInput:
    """Typed input required to persist one trace-report bundle."""

    title: str
    description: str | None
    page_url: str | None
    thread_id: str
    agent_name: str
    user_agent: str | None
    console_log_json: str | None
    run_history: list[ThreadRunHistoryEntry]


@dataclass(frozen=True, slots=True)
class TraceReportResult:
    """Output metadata returned after a trace-report bundle is persisted."""

    trace_id: str
    directory: str
    trace_json_path: str
    markdown_path: str


@dataclass(frozen=True, slots=True)
class RecentTraceReport:
    """Small summary item used by the recent-trace diagnostics surface."""

    trace_id: str
    title: str
    created_at: str
    thread_id: str | None
    agent_name: str | None
    directory: str
    markdown_path: str


class TraceReportWriter:
    """Persist trace bundles to a local traces directory for debugging workflows."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def write_bundle(self, payload: TraceReportInput) -> TraceReportResult:
        """Create one trace-report bundle with canonical JSON and markdown summary."""

        normalized_title = payload.title.strip()
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        trace_id = f"{_slugify(normalized_title)}--{timestamp}"
        bundle_dir = self._root_dir / trace_id
        bundle_dir.mkdir(parents=True, exist_ok=False)

        metadata = {
            "trace_id": trace_id,
            "title": normalized_title,
            "description": payload.description,
            "created_at": datetime.now(UTC).isoformat(),
            "page_url": payload.page_url,
            "thread_id": payload.thread_id,
            "agent_name": payload.agent_name,
            "user_agent": payload.user_agent,
            "run_count": len(payload.run_history),
        }
        (bundle_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

        trace_path = bundle_dir / "trace.json"
        trace_path.write_text(
            json.dumps(_build_trace_payload(payload), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

        if payload.console_log_json:
            redacted_console = _redact_json_text(payload.console_log_json)
            (bundle_dir / "console_log.json").write_text(
                json.dumps(redacted_console, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )

        markdown_path = bundle_dir / "report.md"
        markdown_path.write_text(_build_markdown(payload, trace_id), encoding="utf-8")
        return TraceReportResult(
            trace_id=trace_id,
            directory=str(bundle_dir),
            trace_json_path=str(trace_path),
            markdown_path=str(markdown_path),
        )

    def list_recent(self, *, limit: int = 5) -> list[RecentTraceReport]:
        """Return recent saved trace bundles for lightweight diagnostics surfaces."""

        bundle_dirs = sorted(
            [path for path in self._root_dir.iterdir() if path.is_dir()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        recent: list[RecentTraceReport] = []
        for bundle_dir in bundle_dirs[: max(limit, 0)]:
            metadata_path = bundle_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            metadata = cast(
                "dict[str, object]", json.loads(metadata_path.read_text(encoding="utf-8"))
            )
            recent.append(
                RecentTraceReport(
                    trace_id=str(metadata.get("trace_id") or bundle_dir.name),
                    title=str(metadata.get("title") or bundle_dir.name),
                    created_at=str(metadata.get("created_at") or ""),
                    thread_id=_optional_string(metadata.get("thread_id")),
                    agent_name=_optional_string(metadata.get("agent_name")),
                    directory=str(bundle_dir),
                    markdown_path=str(bundle_dir / "report.md"),
                )
            )
        return recent


def _build_trace_payload(payload: TraceReportInput) -> dict[str, object]:
    runs: list[dict[str, object]] = []
    flattened_events: list[object] = []
    for entry in payload.run_history:
        events = _redact_value(_json_or_fallback(entry.agui_event_trace_json))
        if isinstance(events, list):
            flattened_events.extend(events)
        runs.append(
            {
                "run_id": entry.run_id,
                "parent_run_id": entry.parent_run_id,
                "agent_name": entry.agent_name,
                "status": entry.status,
                "user_prompt_text": _redact_value(entry.user_prompt_text),
                "started_at": entry.started_at,
                "ended_at": entry.ended_at,
                "agui_input_messages": _redact_value(
                    _json_or_fallback(entry.agui_input_messages_json)
                ),
                "agui_events": events,
                "pydantic_all_messages": _redact_value(
                    _json_or_fallback(entry.pydantic_all_messages_json)
                ),
                "pydantic_new_messages": _redact_value(
                    _json_or_fallback(entry.pydantic_new_messages_json)
                ),
            }
        )
    return {
        "title": payload.title,
        "description": payload.description,
        "thread_id": payload.thread_id,
        "agent_name": payload.agent_name,
        "page_url": payload.page_url,
        "run_count": len(runs),
        "event_count": len(flattened_events),
        "runs": runs,
        "events": flattened_events,
    }


def _build_markdown(payload: TraceReportInput, trace_id: str) -> str:
    lines = [
        f"# {payload.title}",
        "",
        "## Summary",
        f"- `trace_id`: {trace_id}",
        f"- `thread_id`: {payload.thread_id}",
        f"- `agent_name`: {payload.agent_name}",
        f"- `run_count`: {len(payload.run_history)}",
    ]
    if payload.description:
        lines.extend(["", "## Description", payload.description])
    lines.extend(
        [
            "",
            "## Files",
            "- `trace.json`: Canonical redacted current-agent thread trace payload.",
            "- `metadata.json`: Save metadata for the trace report.",
            "- `report.md`: Human-readable summary and run inventory.",
        ]
    )
    if payload.console_log_json:
        lines.append(
            "- `console_log.json`: Redacted browser console snapshot captured at save time."
        )
    lines.extend(["", "## Runs"])
    for entry in payload.run_history:
        lines.append(f"- `{entry.run_id}` · status={entry.status} · started_at={entry.started_at}")
        if entry.user_prompt_text:
            lines.append(f"  - prompt: {_redact_string(entry.user_prompt_text)}")
    lines.append("")
    return "\n".join(lines)


def _slugify(value: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (collapsed or "trace_report")[:_MAX_SLUG_LENGTH]


def _json_or_fallback(raw: str | None) -> object:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _redact_json_text(raw_json: str) -> JsonValue:
    try:
        parsed = cast("JsonValue", json.loads(raw_json))
    except json.JSONDecodeError:
        return _redact_string(raw_json)
    return cast("JsonValue", _redact_value(parsed))


def _redact_value(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, nested in value.items():
            if _SENSITIVE_KEY_PATTERN.search(key):
                redacted[key] = REDACTED_VALUE
            else:
                redacted[key] = _redact_value(nested)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _redact_string(value: str) -> str:
    if _SENSITIVE_KEY_PATTERN.search(value):
        return REDACTED_VALUE
    return value


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None
