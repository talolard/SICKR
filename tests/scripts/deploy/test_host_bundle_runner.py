from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.deploy import host_bundle_runner

_BACKEND_REPOSITORY = "046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend"
_UI_REPOSITORY = "046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/ui"


def _write_bundle(tmp_path: Path, *, release_tag: str = "v1.4.2") -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "scripts").mkdir()
    host_bootstrap_root = tmp_path / "host-bootstrap"
    run_id = "pilot-1000-20260318b"
    catalog_path = host_bootstrap_root / "ikea_image_catalog" / "runs" / run_id / "catalog.parquet"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text("catalog-bytes\n", encoding="utf-8")
    backend_digest = "sha256:" + "2" * 64
    ui_digest = "sha256:" + "1" * 64
    (bundle_dir / "host.env").write_text(
        "\n".join(
            [
                "AWS_REGION=eu-central-1",
                "COMPOSE_PROJECT_NAME=ikea-agent-dev",
                "PRODUCT_IMAGE_BASE_URL=https://designagent.talperry.com/static/product-images",
                "BACKEND_IMAGE_REF=" + _BACKEND_REPOSITORY + "@" + backend_digest,
                "UI_IMAGE_REF=" + _UI_REPOSITORY + "@" + ui_digest,
                "BACKEND_APP_SECRET_ARN=arn:aws:backend",
                "MODEL_PROVIDER_SECRET_ARN=arn:aws:model",
                "OBSERVABILITY_SECRET_ARN=arn:aws:obs",
                "DATABASE_SECRET_ARN=arn:aws:db",
                "BACKEND_HOST_PORT=8000",
                "UI_HOST_PORT=3000",
                "BACKEND_SECRETS_ENV_FILE="
                + str(tmp_path / "state" / "runtime" / "backend.secrets.env"),
                "HOST_BOOTSTRAP_ROOT_DIR=" + str(host_bootstrap_root),
                "RELEASE_GIT_TAG=" + release_tag,
                "RELEASE_GIT_SHA=abc1234def5678",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "backend.env").write_text("APP_ENV=dev\n", encoding="utf-8")
    (bundle_dir / "ui.env").write_text("NODE_ENV=production\n", encoding="utf-8")
    (bundle_dir / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (bundle_dir / "release-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "app_version": "1.4.2",
                "git_tag": release_tag,
                "git_sha": "abc1234def5678",
                "bootstrap": {
                    "postgres_seed_version": "a" * 64,
                    "image_catalog_run_id": run_id,
                },
                "ui_image": {
                    "repository": _UI_REPOSITORY,
                    "version_tag": release_tag,
                    "commit_tag": "sha-abc1234def5678",
                    "digest": ui_digest,
                    "image_ref": _UI_REPOSITORY + ":" + release_tag,
                    "digest_ref": _UI_REPOSITORY + "@" + ui_digest,
                },
                "backend_image": {
                    "repository": _BACKEND_REPOSITORY,
                    "version_tag": release_tag,
                    "commit_tag": "sha-abc1234def5678",
                    "digest": backend_digest,
                    "image_ref": _BACKEND_REPOSITORY + ":" + release_tag,
                    "digest_ref": _BACKEND_REPOSITORY + "@" + backend_digest,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle_dir


def test_deploy_bundle_runs_expected_sequence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle_dir = _write_bundle(tmp_path)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    commands: list[list[str]] = []
    waits: list[str] = []

    def _fake_secrets(_host_env: dict[str, str]) -> dict[str, str]:
        return {"DATABASE_URL": "postgres://example", "GEMINI_API_KEY": "token"}

    def _fake_login(_host_env: dict[str, str]) -> None:
        return None

    def _fake_run_command(
        args: list[str], *, cwd: Path | None = None, input_text: str | None = None
    ) -> str:
        del cwd, input_text
        commands.append(args)
        return ""

    def _fake_wait(url: str, *, timeout_seconds: int) -> None:
        del timeout_seconds
        waits.append(url)

    monkeypatch.setattr(host_bundle_runner, "_merged_backend_secrets", _fake_secrets)
    monkeypatch.setattr(host_bundle_runner, "_login_ecr", _fake_login)
    monkeypatch.setattr(host_bundle_runner, "_run_command", _fake_run_command)
    monkeypatch.setattr(host_bundle_runner, "_wait_for_http_success", _fake_wait)

    host_bundle_runner._deploy_bundle(
        bundle_dir=bundle_dir,
        state_dir=state_dir,
        run_migrations=True,
        run_bootstrap=True,
    )

    assert (state_dir / "runtime" / "backend.secrets.env").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "DATABASE_URL=postgres://example",
        "GEMINI_API_KEY=token",
    ]
    assert commands[0][-3:] == ["pull", "backend", "ui"]
    assert "scripts.deploy.apply_migrations" in commands[1]
    assert "scripts.deploy.bootstrap_catalog" in commands[2]
    assert "--image-catalog-run-id" in commands[2]
    assert "pilot-1000-20260318b" in commands[2]
    assert "scripts.deploy.verify_seed_state" in commands[3]
    assert "--expected-postgres-seed-version" in commands[3]
    assert "a" * 64 in commands[3]
    assert "--expected-image-catalog-seed-version" in commands[3]
    assert commands[4][-2:] == ["-d", "backend"]
    assert commands[5][-2:] == ["-d", "ui"]
    assert waits == [
        "http://127.0.0.1:8000/api/health/live",
        "http://127.0.0.1:8000/api/health/ready",
        "http://127.0.0.1:3000/api/health",
        "http://127.0.0.1:3000/api/agents",
        "http://127.0.0.1:3000/agents/search",
    ]
    assert (state_dir / "current_release_tag.txt").read_text(encoding="utf-8").strip() == "v1.4.2"


def test_rollback_previous_uses_previous_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_dir = tmp_path / "state"
    release_dir = state_dir / "releases" / "v1.4.1"
    release_dir.mkdir(parents=True)
    (state_dir / "previous_release_tag.txt").write_text("v1.4.1\n", encoding="utf-8")
    called: dict[str, object] = {}

    def _fake_deploy_bundle(
        *, bundle_dir: Path, state_dir: Path, run_migrations: bool, run_bootstrap: bool
    ) -> None:
        called["bundle_dir"] = bundle_dir
        called["state_dir"] = state_dir
        called["run_migrations"] = run_migrations
        called["run_bootstrap"] = run_bootstrap

    monkeypatch.setattr(host_bundle_runner, "_deploy_bundle", _fake_deploy_bundle)

    host_bundle_runner._rollback_previous(state_dir=state_dir)

    assert called == {
        "bundle_dir": release_dir,
        "state_dir": state_dir,
        "run_migrations": False,
        "run_bootstrap": False,
    }


def test_deploy_bundle_rejects_manifest_env_mismatch(tmp_path: Path) -> None:
    bundle_dir = _write_bundle(tmp_path)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    host_env_path = bundle_dir / "host.env"
    host_env_path.write_text(
        host_env_path.read_text(encoding="utf-8").replace(
            "RELEASE_GIT_TAG=v1.4.2", "RELEASE_GIT_TAG=v9.9.9"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="release tag"):
        host_bundle_runner._deploy_bundle(
            bundle_dir=bundle_dir,
            state_dir=state_dir,
            run_migrations=False,
            run_bootstrap=False,
        )
