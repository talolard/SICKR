from __future__ import annotations

import sys

import pytest

from ikea_agent.chat_app import runserver


def test_main_runs_chat_app_with_parsed_cli_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_app = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(runserver, "create_app", lambda: sentinel_app)
    monkeypatch.setattr(
        runserver.uvicorn,
        "run",
        lambda app, *, host, port, reload: captured.update(
            {
                "app": app,
                "host": host,
                "port": port,
                "reload": reload,
            }
        ),
    )
    monkeypatch.setattr(sys, "argv", ["runserver", "--host", "127.0.0.1", "--port", "9001"])

    runserver.main()

    assert captured == {
        "app": sentinel_app,
        "host": "127.0.0.1",
        "port": 9001,
        "reload": False,
    }
