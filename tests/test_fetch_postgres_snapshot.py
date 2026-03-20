from __future__ import annotations

import json
from pathlib import Path

from scripts.docker_deps.fetch_postgres_snapshot import (
    ArtifactRef,
    WorkflowRunRef,
    _choose_workflow_run,
    _repo_name_from_remote_url,
    _resolve_downloaded_snapshot,
    _write_latest_snapshot_metadata,
)


def test_repo_name_from_remote_url_supports_ssh_and_https() -> None:
    assert _repo_name_from_remote_url("git@github.com:talolard/SICKR.git") == "talolard/SICKR"
    assert _repo_name_from_remote_url("https://github.com/talolard/SICKR.git") == "talolard/SICKR"


def test_choose_workflow_run_prefers_exact_branch_sha() -> None:
    selected, used_default_branch_fallback = _choose_workflow_run(
        current_branch="feature/postgres-snapshot",
        current_head_sha="abc123",
        default_branch="main",
        current_branch_runs=[
            WorkflowRunRef(
                run_id=12,
                head_branch="feature/postgres-snapshot",
                head_sha="abc123",
                html_url="https://example.test/runs/12",
            ),
            WorkflowRunRef(
                run_id=11,
                head_branch="feature/postgres-snapshot",
                head_sha="older",
                html_url="https://example.test/runs/11",
            ),
        ],
        default_branch_runs=[
            WorkflowRunRef(
                run_id=9,
                head_branch="main",
                head_sha="mainsha",
                html_url="https://example.test/runs/9",
            )
        ],
    )

    assert selected is not None
    assert selected.run_id == 12
    assert used_default_branch_fallback is False


def test_choose_workflow_run_falls_back_to_default_branch() -> None:
    selected, used_default_branch_fallback = _choose_workflow_run(
        current_branch="feature/postgres-snapshot",
        current_head_sha="missing",
        default_branch="main",
        current_branch_runs=[
            WorkflowRunRef(
                run_id=11,
                head_branch="feature/postgres-snapshot",
                head_sha="older",
                html_url="https://example.test/runs/11",
            )
        ],
        default_branch_runs=[
            WorkflowRunRef(
                run_id=9,
                head_branch="main",
                head_sha="mainsha",
                html_url="https://example.test/runs/9",
            )
        ],
    )

    assert selected is not None
    assert selected.run_id == 9
    assert used_default_branch_fallback is True


def test_resolve_downloaded_snapshot_reads_manifest_and_dump(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "downloads" / "postgres-snapshot" / "pgsnapshot-1"
    artifact_dir.mkdir(parents=True)
    dump_path = artifact_dir / "postgres.dump"
    dump_path.write_bytes(b"snapshot")
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"snapshot_version": "pgsnapshot-1"}) + "\n", encoding="utf-8"
    )

    resolved_dump_path, resolved_manifest_path, snapshot_version = _resolve_downloaded_snapshot(
        tmp_path
    )

    assert resolved_dump_path == dump_path.resolve()
    assert resolved_manifest_path == manifest_path.resolve()
    assert snapshot_version == "pgsnapshot-1"


def test_write_latest_snapshot_metadata_records_published_source(tmp_path: Path) -> None:
    output_root = tmp_path / "snapshots"
    output_root.mkdir()
    artifact_path = (output_root / "downloads" / "run-7" / "postgres.dump").resolve()
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"snapshot")
    manifest_path = artifact_path.with_name("manifest.json")
    manifest_path.write_text(
        json.dumps({"snapshot_version": "pgsnapshot-7"}) + "\n", encoding="utf-8"
    )

    latest_path = _write_latest_snapshot_metadata(
        output_root=output_root,
        repo="talolard/SICKR",
        default_branch="main",
        run_ref=WorkflowRunRef(
            run_id=7,
            head_branch="feature/postgres-snapshot",
            head_sha="abc123",
            html_url="https://example.test/runs/7",
        ),
        artifact=ArtifactRef(
            artifact_id=100,
            name="postgres-snapshot-pgsnapshot-7",
            digest="sha256:test",
        ),
        artifact_path=artifact_path,
        manifest_path=manifest_path,
        snapshot_version="pgsnapshot-7",
        used_default_branch_fallback=False,
    )

    payload = json.loads(latest_path.read_text(encoding="utf-8"))

    assert payload["source_kind"] == "github_actions_artifact"
    assert payload["workflow_run_id"] == 7
    assert payload["artifact_path"] == str(artifact_path)
    assert payload["snapshot_version"] == "pgsnapshot-7"
