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
        "ARTIFACT_STORAGE_BACKEND",
        "ARTIFACT_S3_BUCKET",
        "ARTIFACT_S3_PREFIX",
        "ARTIFACT_S3_REGION",
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
    assert settings.artifact_storage_backend == "local_disk"


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
def test_app_settings_accepts_private_s3_artifact_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARTIFACT_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("ARTIFACT_S3_BUCKET", "private-artifacts")
    monkeypatch.setenv("ARTIFACT_S3_PREFIX", "dev")
    monkeypatch.setenv("ARTIFACT_S3_REGION", "eu-central-1")

    settings = AppSettings(_env_file=None)

    assert settings.artifact_storage_backend == "s3"
    assert settings.artifact_s3_bucket == "private-artifacts"
    assert settings.artifact_s3_prefix == "dev"
    assert settings.artifact_s3_region == "eu-central-1"


@pytest.mark.usefixtures("_clear_model_setting_env")
def test_app_settings_accepts_app_logfire_token_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_logfire_value = "sample-logfire-setting"
    monkeypatch.setenv("APP_LOGFIRE_TOKEN", expected_logfire_value)

    settings = AppSettings(_env_file=None)

    assert settings.logfire_token == expected_logfire_value
