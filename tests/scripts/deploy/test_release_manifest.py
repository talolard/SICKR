from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deploy.read_release_version import read_release_version
from scripts.deploy.release_manifest import read_release_manifest
from scripts.deploy.write_release_manifest import main as write_release_manifest_main


def test_read_release_version_accepts_plain_semver(tmp_path: Path) -> None:
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.2.3\n", encoding="utf-8")

    assert read_release_version(version_file) == "1.2.3"


def test_read_release_version_rejects_prefixed_values(tmp_path: Path) -> None:
    version_file = tmp_path / "version.txt"
    version_file.write_text("v1.2.3\n", encoding="utf-8")

    with pytest.raises(ValueError, match="plain semver"):
        read_release_version(version_file)


def test_write_release_manifest_writes_expected_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "release-manifest.json"
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
            "--postgres-seed-version",
            "a" * 64,
            "--image-catalog-run-id",
            "pilot-1000-20260318b",
            "--ui-repository",
            "046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/ui",
            "--ui-digest",
            "sha256:" + "1" * 64,
            "--backend-repository",
            "046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend",
            "--backend-digest",
            "sha256:" + "2" * 64,
            "--output",
            str(output_path),
        ],
    )

    assert write_release_manifest_main() == 0

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["app_version"] == "1.4.2"
    assert manifest["git_tag"] == "v1.4.2"
    assert manifest["git_sha"] == "abc1234def5678"
    assert manifest["bootstrap"]["postgres_seed_version"] == "a" * 64
    assert manifest["bootstrap"]["image_catalog_run_id"] == "pilot-1000-20260318b"
    assert manifest["ui_image"]["version_tag"] == "v1.4.2"
    assert manifest["ui_image"]["commit_tag"] == "sha-abc1234def5678"
    assert manifest["ui_image"]["digest_ref"].endswith("@" + "sha256:" + "1" * 64)
    assert manifest["backend_image"]["digest_ref"].endswith("@" + "sha256:" + "2" * 64)


def test_read_release_manifest_round_trips_written_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "release-manifest.json"
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
            "--postgres-seed-version",
            "a" * 64,
            "--image-catalog-run-id",
            "pilot-1000-20260318b",
            "--ui-repository",
            "repo/ui",
            "--ui-digest",
            "sha256:" + "1" * 64,
            "--backend-repository",
            "repo/backend",
            "--backend-digest",
            "sha256:" + "2" * 64,
            "--output",
            str(output_path),
        ],
    )

    assert write_release_manifest_main() == 0

    manifest = read_release_manifest(output_path)
    assert manifest.app_version == "1.4.2"
    assert manifest.git_tag == "v1.4.2"
    assert manifest.bootstrap.postgres_seed_version == "a" * 64
    assert manifest.bootstrap.image_catalog_run_id == "pilot-1000-20260318b"
    assert manifest.ui_image.digest_ref == f"repo/ui@{'sha256:' + '1' * 64}"
    assert manifest.backend_image.digest_ref == f"repo/backend@{'sha256:' + '2' * 64}"


def test_write_release_manifest_rejects_mismatched_tag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "release-manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "write_release_manifest.py",
            "--app-version",
            "1.4.2",
            "--git-tag",
            "v1.4.3",
            "--git-sha",
            "abc1234def5678",
            "--postgres-seed-version",
            "a" * 64,
            "--image-catalog-run-id",
            "pilot-1000-20260318b",
            "--ui-repository",
            "repo/ui",
            "--ui-digest",
            "sha256:" + "1" * 64,
            "--backend-repository",
            "repo/backend",
            "--backend-digest",
            "sha256:" + "2" * 64,
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(ValueError, match="Expected git_tag"):
        write_release_manifest_main()


def test_read_release_manifest_rejects_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "release-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "app_version": "1.0.0",
                "git_tag": "v1.0.0",
                "git_sha": "abc1234",
                "bootstrap": {
                    "postgres_seed_version": "a" * 64,
                    "image_catalog_run_id": "pilot-1000-20260318b",
                },
                "ui_image": {"repository": "repo/ui", "digest": "sha256:" + "1" * 64},
                "backend_image": {
                    "repository": "repo/backend",
                    "digest": "sha256:" + "2" * 64,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema_version 2"):
        read_release_manifest(path)


def test_write_release_manifest_rejects_invalid_image_catalog_run_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "release-manifest.json"
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
            "--postgres-seed-version",
            "a" * 64,
            "--image-catalog-run-id",
            "../escape",
            "--ui-repository",
            "repo/ui",
            "--ui-digest",
            "sha256:" + "1" * 64,
            "--backend-repository",
            "repo/backend",
            "--backend-digest",
            "sha256:" + "2" * 64,
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(ValueError, match="run id"):
        write_release_manifest_main()
