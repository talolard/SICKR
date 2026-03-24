from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deploy.build_release_bundle import main as build_release_bundle_main
from scripts.deploy.write_release_manifest import main as write_release_manifest_main


def _write_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    manifest_path = tmp_path / "release-manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "write_release_manifest.py",
            "--app-version",
            "1.4.2",
            "--git-tag",
            "v1.4.2",
            "--git-sha",
            "abc1234def5678",
            "--ui-repository",
            "046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/ui",
            "--ui-digest",
            "sha256:" + "1" * 64,
            "--backend-repository",
            "046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend",
            "--backend-digest",
            "sha256:" + "2" * 64,
            "--output",
            str(manifest_path),
        ],
    )
    assert write_release_manifest_main() == 0
    return manifest_path


def test_build_release_bundle_writes_expected_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path = _write_manifest(tmp_path, monkeypatch)
    output_dir = tmp_path / "bundle"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_release_bundle.py",
            "--release-manifest",
            str(manifest_path),
            "--output-dir",
            str(output_dir),
            "--backend-app-secret-arn",
            "arn:aws:secretsmanager:eu-central-1:046673074482:secret:backend",
            "--model-provider-secret-arn",
            "arn:aws:secretsmanager:eu-central-1:046673074482:secret:model",
            "--observability-secret-arn",
            "arn:aws:secretsmanager:eu-central-1:046673074482:secret:obs",
            "--database-secret-arn",
            "arn:aws:secretsmanager:eu-central-1:046673074482:secret:db",
        ],
    )

    assert build_release_bundle_main() == 0

    assert (output_dir / "docker-compose.yml").exists()
    assert (output_dir / "scripts" / "host_bundle_runner.py").exists()
    assert (output_dir / "backend.secrets.env").read_text(encoding="utf-8") == "\n"

    host_env = (output_dir / "host.env").read_text(encoding="utf-8")
    assert "RELEASE_GIT_TAG=v1.4.2" in host_env
    assert (
        "BACKEND_IMAGE_REF=046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend@"
    ) in host_env
    assert (
        "MODEL_PROVIDER_SECRET_ARN=arn:aws:secretsmanager:eu-central-1:046673074482:secret:model"
    ) in host_env

    backend_env = (output_dir / "backend.env").read_text(encoding="utf-8")
    assert "LOGFIRE_SERVICE_VERSION=1.4.2" in backend_env
    assert (
        "IMAGE_SERVICE_BASE_URL=https://designagent.talperry.com/static/product-images"
    ) in backend_env

    manifest = json.loads((output_dir / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["git_tag"] == "v1.4.2"
