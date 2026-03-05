from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient

from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.main import create_app


def test_create_app_without_mount_has_no_custom_routes() -> None:
    client = TestClient(create_app(runtime=cast("ChatRuntime", object()), mount_web_ui=False))

    response = client.get("/")

    assert response.status_code == 404
