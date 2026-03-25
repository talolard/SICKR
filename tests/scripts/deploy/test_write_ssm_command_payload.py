from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deploy.write_ssm_command_payload import main as write_ssm_command_payload_main


def _write_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "scripts").mkdir(parents=True)
    (bundle_dir / "host.env").write_text("RELEASE_GIT_TAG=v1.4.2\n", encoding="utf-8")
    (bundle_dir / "backend.env").write_text("APP_ENV=dev\n", encoding="utf-8")
    (bundle_dir / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (bundle_dir / "scripts" / "host_bundle_runner.py").write_text("print('ok')\n", encoding="utf-8")
    return bundle_dir


def test_write_ssm_command_payload_for_deploy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle_dir = _write_bundle(tmp_path)
    output_path = tmp_path / "payload.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "write_ssm_command_payload.py",
            "--mode",
            "deploy",
            "--bundle-dir",
            str(bundle_dir),
            "--state-dir",
            "/var/lib/ikea-agent/deploy",
            "--output",
            str(output_path),
        ],
    )

    assert write_ssm_command_payload_main() == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    joined = "\n".join(payload["commands"])
    assert "releases/v1.4.2" in joined
    assert "host_bundle_runner.py" in joined
    assert "deploy --bundle-dir" in joined


def test_write_ssm_command_payload_for_rollback_previous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "payload.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "write_ssm_command_payload.py",
            "--mode",
            "rollback-previous",
            "--state-dir",
            "/var/lib/ikea-agent/deploy",
            "--output",
            str(output_path),
        ],
    )

    assert write_ssm_command_payload_main() == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    joined = "\n".join(payload["commands"])
    assert "previous_release_tag.txt" in joined
    assert "rollback-previous --state-dir" in joined
