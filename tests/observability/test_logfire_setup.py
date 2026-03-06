from __future__ import annotations

import pytest
from fastapi import FastAPI

from ikea_agent.config import AppSettings
from ikea_agent.observability import logfire_setup


def _settings(*, token: str | None) -> AppSettings:
    return AppSettings(
        app_env="dev",
        logfire_token=token,
        logfire_send_mode="if-token-present",
        logfire_service_name="ikea-agent",
        logfire_service_version="test-version",
        logfire_environment="dev",
    )


def _reset_logfire_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logfire_setup, "_LOGFIRE_CONFIGURED", False)
    monkeypatch.setattr(logfire_setup, "_PYDANTIC_AI_INSTRUMENTED", False)


def test_configure_logfire_warns_and_continues_when_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_logfire_flags(monkeypatch)
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    configure_call: dict[str, object] | None = None
    pydantic_ai_instrumented = 0
    warned = 0

    def _fake_configure(**kwargs: object) -> None:
        nonlocal configure_call
        configure_call = kwargs

    def _fake_instrument_pydantic_ai() -> None:
        nonlocal pydantic_ai_instrumented
        pydantic_ai_instrumented += 1

    def _fake_warning(
        _message: str,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal warned
        _ = args
        _ = kwargs
        warned += 1

    monkeypatch.setattr(logfire_setup.logfire, "configure", _fake_configure)
    monkeypatch.setattr(
        logfire_setup.logfire,
        "instrument_pydantic_ai",
        _fake_instrument_pydantic_ai,
    )
    monkeypatch.setattr(logfire_setup.logger, "warning", _fake_warning)

    logfire_setup.configure_logfire(_settings(token=None))

    assert warned == 1
    assert pydantic_ai_instrumented == 1
    assert configure_call is not None
    assert configure_call["send_to_logfire"] == "if-token-present"
    assert configure_call["token"] is None


def test_configure_logfire_does_not_warn_when_token_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_logfire_flags(monkeypatch)
    calls: dict[str, int] = {"warned": 0}

    def _fake_warning(
        _message: str,
        *args: object,
        **kwargs: object,
    ) -> None:
        _ = args
        _ = kwargs
        calls["warned"] += 1

    monkeypatch.setattr(logfire_setup.logfire, "configure", lambda **_kwargs: None)
    monkeypatch.setattr(logfire_setup.logfire, "instrument_pydantic_ai", lambda: None)
    monkeypatch.setattr(logfire_setup.logger, "warning", _fake_warning)

    logfire_setup.configure_logfire(_settings(token="token-present"))  # noqa: S106

    assert calls["warned"] == 0


def test_instrument_fastapi_app_calls_logfire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, FastAPI | None] = {"app": None}

    def _fake_instrument_fastapi(app: FastAPI) -> None:
        captured["app"] = app

    monkeypatch.setattr(logfire_setup.logfire, "instrument_fastapi", _fake_instrument_fastapi)
    app = FastAPI()

    logfire_setup.instrument_fastapi_app(app)

    assert captured["app"] is app
