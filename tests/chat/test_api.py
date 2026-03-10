from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import (
    _resolve_subagent_name_from_chat_payload,
    _resolve_subagent_name_from_referer,
    create_app,
)
from ikea_agent.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_app_without_mount_has_no_custom_routes() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    response = client.get("/")
    ag_ui_response = client.get("/ag-ui")

    assert response.status_code == 404
    assert ag_ui_response.status_code == 404


def test_create_app_with_ag_ui_mount_exposes_ag_ui_route() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=True,
        )
    )

    response = client.get("/ag-ui")

    assert response.status_code != 404


def test_subagent_catalog_route_lists_registered_subagents() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    response = client.get("/api/subagents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["subagents"]
    assert any(item["name"] == "floor_plan_intake" for item in payload["subagents"])


def test_subagent_web_mount_exists() -> None:
    client = TestClient(
        create_app(
            runtime=cast("ChatRuntime", object()),
            mount_web_ui=False,
            mount_ag_ui=False,
        )
    )

    response = client.get("/subagents/floor_plan_intake/chat/")
    assert response.status_code != 404


def test_resolve_subagent_name_from_referer_path() -> None:
    assert (
        _resolve_subagent_name_from_referer(
            "http://localhost:8000/subagents/floor_plan_intake/chat/"
        )
        == "floor_plan_intake"
    )
    assert _resolve_subagent_name_from_referer("http://localhost:8000/") is None


def test_resolve_subagent_name_from_chat_payload_model() -> None:
    payload = b'{"model":"function:subagent_floor_plan_intake","messages":[]}'
    resolved = _resolve_subagent_name_from_chat_payload(
        payload,
        model_id_to_subagent={"function:subagent_floor_plan_intake": "floor_plan_intake"},
    )
    assert resolved == "floor_plan_intake"


def test_attachment_upload_and_fetch_round_trip() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    upload_response = client.post(
        "/attachments",
        content=b"fake-image-bytes",
        headers={"content-type": "image/png", "x-filename": "room.png"},
    )

    assert upload_response.status_code == 200
    attachment_ref = upload_response.json()
    assert attachment_ref["attachment_id"]
    assert attachment_ref["uri"].startswith("/attachments/")

    download_response = client.get(attachment_ref["uri"])
    assert download_response.status_code == 200
    assert download_response.content == b"fake-image-bytes"
    assert download_response.headers["content-type"].startswith("image/png")


def test_attachment_upload_rejects_unsupported_type() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    upload_response = client.post(
        "/attachments",
        content=b"not-an-image",
        headers={"content-type": "application/pdf"},
    )

    assert upload_response.status_code == 415


def test_generated_floor_plan_returns_image_tool_output() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.post("/generated-images/floor-plan")
    assert response.status_code == 200
    payload = response.json()
    assert "caption" in payload
    assert payload["images"]
    image_ref = payload["images"][0]
    assert image_ref["mime_type"] == "image/svg+xml"

    image_response = client.get(image_ref["uri"])
    assert image_response.status_code == 200
    assert image_response.headers["content-type"].startswith("image/svg+xml")


@pytest.mark.parametrize(
    ("file_name", "content"),
    [
        ("scene.usda", b'#usda 1.0\ndef Xform "Room" {}'),
        ("scene.usd", b"binary-usd-placeholder"),
        ("scene.usdc", b"binary-usdc-placeholder"),
        ("scene.usdz", b"binary-usdz-placeholder"),
    ],
)
def test_openusd_ingest_accepts_supported_formats(file_name: str, content: bytes) -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.post(
        "/room-3d/openusd-ingest",
        content=content,
        headers={
            "x-filename": file_name,
            "x-thread-id": "thread-openusd",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_asset"]["attachment_id"]
    assert payload["usd_format"] == file_name.rsplit(".", maxsplit=1)[-1]
    assert payload["metadata"]["validation_backend"] in {"fallback", "pxr"}


def test_openusd_ingest_rejects_unsupported_extension() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.post(
        "/room-3d/openusd-ingest",
        content=b"not-usd",
        headers={
            "x-filename": "invalid.txt",
            "x-thread-id": "thread-openusd",
        },
    )

    assert response.status_code == 415
    payload = response.json()
    assert payload["detail"]["code"] == "unsupported_extension"


def test_comment_bundle_route_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("FEEDBACK_CAPTURE_ENABLED", "false")
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.post("/api/comments", json={})

    assert response.status_code == 503


def test_comment_bundle_route_persists_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("FEEDBACK_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("FEEDBACK_ROOT_DIR", str(tmp_path / "comments"))
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    console_payload = json.dumps(
        [
            {"level": "error", "message": "token=abc123", "context": {"api_key": "secret-key"}},
            {"level": "info", "message": "render complete"},
        ]
    )
    ui_state_payload = json.dumps(
        {
            "thread_id": "thread-123",
            "auth_token": "my-sensitive-token",
            "nested": {"password": "do-not-store"},
        }
    )
    first_upload = client.post(
        "/attachments",
        content=b"png-bytes",
        headers={"content-type": "image/png", "x-filename": "render.png"},
    )
    second_upload = client.post(
        "/attachments",
        content=b"jpg-bytes",
        headers={"content-type": "image/jpeg", "x-filename": "render-2.jpg"},
    )
    assert first_upload.status_code == 200
    assert second_upload.status_code == 200
    first_ref = first_upload.json()
    second_ref = second_upload.json()

    response = client.post(
        "/api/comments",
        json={
            "title": "The problem with SVG",
            "comment": "Renderer gets jagged at zoom 2x.",
            "thread_id": "thread-123",
            "page_url": "http://localhost:3000/?thread=thread-123",
            "include_console_log": True,
            "include_dom_snapshot": True,
            "include_ui_state": True,
            "console_log": console_payload,
            "dom_snapshot": "<html><body><div id='app'>Test</div></body></html>",
            "ui_state": ui_state_payload,
            "attachment_ids": [first_ref["attachment_id"], second_ref["attachment_id"]],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comment_id"].startswith("the_problem_with_svg--")
    assert payload["saved_images_count"] == 2
    comment_dir = Path(payload["directory"])
    assert (comment_dir / "comment.md").exists()
    assert (comment_dir / "metadata.json").exists()
    assert (comment_dir / "images").exists()
    assert (comment_dir / "console_log.ndjson").exists()
    assert (comment_dir / "dom_snapshot.html").exists()
    assert (comment_dir / "ui_state.json").exists()

    markdown = (comment_dir / "comment.md").read_text(encoding="utf-8")
    assert "The problem with SVG" in markdown
    assert "Bundle File Guide" in markdown
    assert "console_log.ndjson" in markdown

    ui_state_saved = json.loads((comment_dir / "ui_state.json").read_text(encoding="utf-8"))
    assert isinstance(ui_state_saved["auth_token"], str)
    assert ui_state_saved["auth_token"].startswith("[")
    assert isinstance(ui_state_saved["nested"]["password"], str)
    assert ui_state_saved["nested"]["password"].startswith("[")


def test_comment_bundle_route_uses_default_title_when_blank(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("FEEDBACK_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("FEEDBACK_ROOT_DIR", str(tmp_path / "comments"))
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.post(
        "/api/comments",
        json={"title": "   ", "comment": "No explicit title."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comment_id"].startswith("user_comment_from_ui--")


def test_comment_bundle_route_rejects_empty_default_submission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("FEEDBACK_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("FEEDBACK_ROOT_DIR", str(tmp_path / "comments"))
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.post(
        "/api/comments",
        json={"title": "user_comment_from_ui", "comment": "", "attachment_ids": []},
    )

    assert response.status_code == 422
