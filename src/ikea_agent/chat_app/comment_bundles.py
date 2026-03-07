"""Feedback comment bundle persistence helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

DEFAULT_COMMENT_TITLE = "user_comment_from_ui"
REDACTED_VALUE = "[REDACTED]"
_MAX_SLUG_LENGTH = 80

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:password|passwd|secret|token|api[-_]?key|authorization|cookie|session|bearer)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class FeedbackImageInput:
    """One uploaded image payload from feedback form submission."""

    file_name: str
    mime_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class CommentBundleInput:
    """Typed input required to persist one feedback comment bundle."""

    title: str | None
    comment: str
    page_url: str | None
    thread_id: str | None
    user_agent: str | None
    include_console_log: bool
    include_dom_snapshot: bool
    include_ui_state: bool
    console_log_json: str | None
    dom_snapshot_html: str | None
    ui_state_json: str | None
    images: list[FeedbackImageInput]


@dataclass(frozen=True, slots=True)
class CommentBundleResult:
    """Output metadata returned after a comment bundle is persisted."""

    comment_id: str
    directory: str
    markdown_path: str
    saved_images_count: int


class CommentBundleWriter:
    """Persist feedback bundles to a local comments directory for debugging workflows."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def write_bundle(self, payload: CommentBundleInput) -> CommentBundleResult:
        """Create one comment bundle with markdown summary and optional artifacts."""

        normalized_title = _normalize_title(payload.title)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        comment_id = f"{_slugify(normalized_title)}--{timestamp}"
        bundle_dir = self._root_dir / comment_id
        bundle_dir.mkdir(parents=True, exist_ok=False)

        metadata: dict[str, object] = {
            "comment_id": comment_id,
            "title": normalized_title,
            "created_at": datetime.now(UTC).isoformat(),
            "page_url": payload.page_url,
            "thread_id": payload.thread_id,
            "user_agent": payload.user_agent,
            "include_console_log": payload.include_console_log,
            "include_dom_snapshot": payload.include_dom_snapshot,
            "include_ui_state": payload.include_ui_state,
            "saved_images_count": 0,
        }

        images_index: list[dict[str, str]] = []
        if payload.images:
            images_dir = bundle_dir / "images"
            images_dir.mkdir(exist_ok=True)
            for index, image in enumerate(payload.images, start=1):
                safe_name = _sanitize_filename(image.file_name)
                image_path = images_dir / f"{index:02d}-{safe_name}"
                image_path.write_bytes(image.content)
                images_index.append(
                    {
                        "path": str(image_path.relative_to(bundle_dir)),
                        "mime_type": image.mime_type,
                        "file_name": image.file_name,
                    }
                )

        metadata["saved_images_count"] = len(images_index)
        metadata["images"] = images_index

        if payload.include_console_log and payload.console_log_json:
            console_records = _redact_json_text(payload.console_log_json)
            console_path = bundle_dir / "console_log.ndjson"
            console_path.write_text(_to_ndjson(console_records), encoding="utf-8")
            metadata["console_log_path"] = str(console_path.relative_to(bundle_dir))

        if payload.include_dom_snapshot and payload.dom_snapshot_html:
            dom_path = bundle_dir / "dom_snapshot.html"
            dom_path.write_text(payload.dom_snapshot_html, encoding="utf-8")
            metadata["dom_snapshot_path"] = str(dom_path.relative_to(bundle_dir))

        if payload.include_ui_state and payload.ui_state_json:
            ui_state_records = _redact_json_text(payload.ui_state_json)
            state_path = bundle_dir / "ui_state.json"
            state_path.write_text(
                json.dumps(ui_state_records, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
            metadata["ui_state_path"] = str(state_path.relative_to(bundle_dir))

        metadata_path = bundle_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

        markdown_path = bundle_dir / "comment.md"
        markdown_path.write_text(
            _build_markdown(
                title=normalized_title,
                comment=payload.comment,
                metadata=metadata,
            ),
            encoding="utf-8",
        )

        return CommentBundleResult(
            comment_id=comment_id,
            directory=str(bundle_dir),
            markdown_path=str(markdown_path),
            saved_images_count=len(images_index),
        )


def _normalize_title(raw_title: str | None) -> str:
    if raw_title is None:
        return DEFAULT_COMMENT_TITLE
    stripped = raw_title.strip()
    return stripped or DEFAULT_COMMENT_TITLE


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    if not slug:
        return DEFAULT_COMMENT_TITLE
    return slug[:_MAX_SLUG_LENGTH]


def _sanitize_filename(file_name: str) -> str:
    normalized = file_name.strip() or "image"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)
    return safe[:120]


def _redact_json_text(raw_json: str) -> JsonValue:
    parsed = cast("JsonValue", json.loads(raw_json))
    return _redact_value(parsed)


def _redact_value(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        redacted: dict[str, JsonValue] = {}
        for key, nested in value.items():
            if _SENSITIVE_KEY_PATTERN.search(key):
                redacted[key] = REDACTED_VALUE
            else:
                redacted[key] = _redact_value(nested)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        if _SENSITIVE_KEY_PATTERN.search(value):
            return REDACTED_VALUE
        return value
    return value


def _to_ndjson(value: JsonValue) -> str:
    if isinstance(value, list):
        return "\n".join(json.dumps(item, ensure_ascii=True) for item in value)
    return json.dumps(value, ensure_ascii=True)


def _build_markdown(*, title: str, comment: str, metadata: dict[str, object]) -> str:
    file_guide_lines: list[str] = [
        "## Bundle File Guide",
        "- `comment.md`: Main user feedback note with key metadata and file map.",
        "- `metadata.json`: Structured metadata for machine parsing and quick triage.",
    ]
    if metadata.get("ui_state_path"):
        file_guide_lines.append(
            "- `ui_state.json`: Redacted UI/session state captured at send time."
        )
    if metadata.get("console_log_path"):
        file_guide_lines.append(
            "- `console_log.ndjson`: Redacted browser console/event stream records."
        )
    if metadata.get("dom_snapshot_path"):
        file_guide_lines.append(
            "- `dom_snapshot.html`: DOM snapshot from the browser at report time."
        )
    saved_images_count = metadata.get("saved_images_count")
    if isinstance(saved_images_count, int) and saved_images_count > 0:
        file_guide_lines.append("- `images/`: Uploaded/pasted screenshots attached to this report.")

    metadata_lines = [
        "## Metadata",
        f"- `comment_id`: {metadata.get('comment_id')}",
        f"- `created_at`: {metadata.get('created_at')}",
        f"- `thread_id`: {metadata.get('thread_id')}",
        f"- `page_url`: {metadata.get('page_url')}",
        f"- `saved_images_count`: {metadata.get('saved_images_count')}",
        f"- `include_console_log`: {metadata.get('include_console_log')}",
        f"- `include_dom_snapshot`: {metadata.get('include_dom_snapshot')}",
        f"- `include_ui_state`: {metadata.get('include_ui_state')}",
    ]

    body = [
        f"# {title}",
        "",
        "## Comment",
        comment.strip() or "(No comment body provided.)",
        "",
        *metadata_lines,
        "",
        *file_guide_lines,
        "",
    ]
    return "\n".join(body)
