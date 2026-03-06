from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import create_app


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
