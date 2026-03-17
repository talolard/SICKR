from __future__ import annotations

import pytest

from ikea_agent.config import AppSettings


@pytest.fixture
def _clear_model_setting_env(monkeypatch: pytest.MonkeyPatch) -> None:
    keys = (
        "GEMINI_GENERATION_MODEL",
        "ALLOW_MODEL_REQUESTS",
        "APP_ALLOW_MODEL_REQUESTS",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_runtime_defaults_match_mark_17() -> None:
    settings = AppSettings(_env_file=None)

    assert settings.gemini_generation_model == "gemini-3.1-flash-lite-preview"
    assert settings.allow_model_requests is True


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_accepts_app_allow_model_requests_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ALLOW_MODEL_REQUESTS", "0")

    settings = AppSettings(_env_file=None)

    assert settings.allow_model_requests is False
