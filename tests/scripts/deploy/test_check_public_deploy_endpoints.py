from __future__ import annotations

from types import TracebackType
from typing import Self

import pytest
from httpx import Request, Response
from scripts.deploy.check_public_deploy_endpoints import main


def test_main_validates_public_routes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class DummyClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> bool:
            del exc_type, exc, traceback
            return False

    def _request(_client: DummyClient, base_url: str, check: object) -> Response:
        assert hasattr(check, "path")
        path = check.path
        assert isinstance(path, str)
        request = Request("GET", f"{base_url}{path}")
        if path == "/api/health":
            return Response(200, json={"status": "ok"}, request=request)
        if path == "/api/agents":
            return Response(200, json={"agents": [{"name": "search"}]}, request=request)
        if path == "/api/agents/search/metadata":
            return Response(
                200,
                json={"name": "search", "agent_key": "agent_search"},
                request=request,
            )
        return Response(404, json={"error": "unexpected"}, request=request)

    monkeypatch.setattr(
        "scripts.deploy.check_public_deploy_endpoints.httpx.Client",
        DummyClient,
    )
    monkeypatch.setattr(
        "scripts.deploy.check_public_deploy_endpoints._request",
        _request,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["check_public_deploy_endpoints.py", "--base-url", "https://designagent.talperry.com"],
    )

    assert main() == 0
    assert "Validated public agent routes" in capsys.readouterr().out
