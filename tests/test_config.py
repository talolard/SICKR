from __future__ import annotations

import pytest

from ikea_agent.config import AppSettings


@pytest.fixture
def _clear_model_setting_env(monkeypatch: pytest.MonkeyPatch) -> None:
    keys = (
        "GEMINI_GENERATION_MODEL",
        "ALLOW_MODEL_REQUESTS",
        "APP_ALLOW_MODEL_REQUESTS",
        "DATABASE_URL",
        "APP_ENV",
        "LOGFIRE_ENVIRONMENT",
        "LOGFIRE_SERVICE_VERSION",
        "IMAGE_SERVING_STRATEGY",
        "IMAGE_SERVICE_BASE_URL",
        "LOGFIRE_TOKEN",
        "APP_LOGFIRE_TOKEN",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_runtime_defaults_match_mark_17() -> None:
    settings = AppSettings(_env_file=None)

    assert settings.gemini_generation_model == "gemini-3.1-flash-lite-preview"
    assert settings.allow_model_requests is True
    assert settings.database_url == "postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent"


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_accepts_app_allow_model_requests_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ALLOW_MODEL_REQUESTS", "0")

    settings = AppSettings(_env_file=None)

    assert settings.allow_model_requests is False


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_accepts_deployed_runtime_contract_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("LOGFIRE_ENVIRONMENT", "dev")
    monkeypatch.setenv("LOGFIRE_SERVICE_VERSION", "1.2.3")
    monkeypatch.setenv("IMAGE_SERVING_STRATEGY", "direct_public_url")
    monkeypatch.setenv(
        "IMAGE_SERVICE_BASE_URL",
        "https://designagent.talperry.com/static/product-images",
    )

    settings = AppSettings(_env_file=None)

    assert settings.app_env == "dev"
    assert settings.logfire_environment == "dev"
    assert settings.logfire_service_version == "1.2.3"
    assert settings.image_serving_strategy == "direct_public_url"
    assert (
        settings.image_service_base_url == "https://designagent.talperry.com/static/product-images"
    )


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_accepts_app_logfire_token_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_logfire_value = "sample-logfire-setting"
    monkeypatch.setenv("APP_LOGFIRE_TOKEN", expected_logfire_value)

    settings = AppSettings(_env_file=None)

    assert settings.logfire_token == expected_logfire_value
