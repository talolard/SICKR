"""Fetch a published Postgres snapshot artifact into a worktree-local cache."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from shutil import which
from urllib.parse import quote

_ARTIFACT_PREFIX = "postgres-snapshot-"
_LATEST_FILENAME = "latest.json"
_WORKFLOW_FILE = "postgres-snapshot.yml"


@dataclass(frozen=True, slots=True)
class WorkflowRunRef:
    """One successful workflow run that can provide a snapshot artifact."""

    run_id: int
    head_branch: str
    head_sha: str
    html_url: str


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """One downloadable artifact attached to a workflow run."""

    artifact_id: int
    name: str
    digest: str | None


@dataclass(frozen=True, slots=True)
class FetchSummary:
    """Observable result of fetching one published snapshot artifact."""

    artifact_name: str
    artifact_path: str
    default_branch: str
    head_branch: str
    head_sha: str
    latest_path: str
    manifest_path: str
    repo: str
    run_id: int
    snapshot_version: str
    used_default_branch_fallback: bool


def main() -> None:
    """Download and register the best published snapshot for this checkout."""

    args = _parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    repo = args.repo or _resolve_repo_name(repo_root)
    default_branch = args.default_branch or _resolve_default_branch(repo_root=repo_root, repo=repo)
    current_branch = args.branch or _git_output(
        repo_root,
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    )
    current_head_sha = args.head_sha or _git_output(repo_root, "rev-parse", "HEAD")
    summary = fetch_postgres_snapshot(
        repo=repo,
        output_root=output_root,
        default_branch=default_branch,
        current_branch=current_branch,
        current_head_sha=current_head_sha,
    )
    summary_json = json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n"
    if args.summary_path is not None:
        summary_path = Path(args.summary_path).expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary_json, encoding="utf-8")
    print(summary_json, end="")


def fetch_postgres_snapshot(
    *,
    repo: str,
    output_root: Path,
    default_branch: str,
    current_branch: str,
    current_head_sha: str,
) -> FetchSummary:
    """Fetch the safest published snapshot artifact for one worktree checkout."""

    output_root.mkdir(parents=True, exist_ok=True)
    current_branch_runs = _list_successful_workflow_runs(
        repo=repo,
        workflow_file=_WORKFLOW_FILE,
        branch=current_branch,
    )
    default_branch_runs = (
        current_branch_runs
        if current_branch == default_branch
        else _list_successful_workflow_runs(
            repo=repo,
            workflow_file=_WORKFLOW_FILE,
            branch=default_branch,
        )
    )
    run_ref, used_default_branch_fallback = _choose_workflow_run(
        current_branch=current_branch,
        current_head_sha=current_head_sha,
        default_branch=default_branch,
        current_branch_runs=current_branch_runs,
        default_branch_runs=default_branch_runs,
    )
    if run_ref is None:
        msg = (
            "No compatible published Postgres snapshot artifact was found. "
            "Run `bash scripts/worktree/deps.sh build-snapshot --slot <n>` to build one locally."
        )
        raise RuntimeError(msg)
    artifact = _select_snapshot_artifact(repo=repo, run_id=run_ref.run_id)
    download_root = output_root / "downloads" / f"run-{run_ref.run_id}"
    if download_root.exists():
        shutil.rmtree(download_root)
    download_root.mkdir(parents=True, exist_ok=True)
    _download_snapshot_artifact(
        repo=repo,
        run_id=run_ref.run_id,
        artifact_name=artifact.name,
        destination=download_root,
    )
    artifact_path, manifest_path, snapshot_version = _resolve_downloaded_snapshot(download_root)
    latest_path = _write_latest_snapshot_metadata(
        output_root=output_root,
        repo=repo,
        default_branch=default_branch,
        run_ref=run_ref,
        artifact=artifact,
        artifact_path=artifact_path,
        manifest_path=manifest_path,
        snapshot_version=snapshot_version,
        used_default_branch_fallback=used_default_branch_fallback,
    )
    return FetchSummary(
        artifact_name=artifact.name,
        artifact_path=str(artifact_path),
        default_branch=default_branch,
        head_branch=run_ref.head_branch,
        head_sha=run_ref.head_sha,
        latest_path=str(latest_path),
        manifest_path=str(manifest_path),
        repo=repo,
        run_id=run_ref.run_id,
        snapshot_version=snapshot_version,
        used_default_branch_fallback=used_default_branch_fallback,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a published Postgres snapshot artifact.")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument(
        "--output-root",
        default=str(Path.cwd() / ".tmp_untracked" / "docker-deps" / "snapshots"),
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument("--default-branch", default=None)
    parser.add_argument("--branch", default=None)
    parser.add_argument("--head-sha", default=None)
    parser.add_argument("--summary-path", default=None)
    return parser.parse_args()


def _choose_workflow_run(
    *,
    current_branch: str,
    current_head_sha: str,
    default_branch: str,
    current_branch_runs: list[WorkflowRunRef],
    default_branch_runs: list[WorkflowRunRef],
) -> tuple[WorkflowRunRef | None, bool]:
    """Choose the safest available workflow run for this checkout."""

    for run_ref in current_branch_runs:
        if run_ref.head_sha == current_head_sha:
            return run_ref, False
    if current_branch != default_branch and default_branch_runs:
        return default_branch_runs[0], True
    return (current_branch_runs[0], False) if current_branch_runs else (None, False)


def _resolve_repo_name(repo_root: Path) -> str:
    remote_url = _git_output(repo_root, "config", "--get", "remote.origin.url")
    return _repo_name_from_remote_url(remote_url)


def _resolve_default_branch(*, repo_root: Path, repo: str) -> str:
    try:
        symbolic_ref = _git_output(repo_root, "symbolic-ref", "refs/remotes/origin/HEAD")
    except RuntimeError:
        repo_payload = _gh_api_json(f"repos/{repo}")
        default_branch = repo_payload.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            msg = f"Could not resolve the default branch for {repo}."
            raise RuntimeError(msg) from None
        return default_branch
    return symbolic_ref.rsplit("/", maxsplit=1)[-1]


def _repo_name_from_remote_url(remote_url: str) -> str:
    normalized = remote_url.strip().removesuffix(".git")
    prefixes = (
        "git@github.com:",
        "ssh://git@github.com/",
        "https://github.com/",
        "http://github.com/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix)
    msg = f"Unsupported GitHub remote URL: {remote_url}"
    raise ValueError(msg)


def _list_successful_workflow_runs(
    *,
    repo: str,
    workflow_file: str,
    branch: str,
) -> list[WorkflowRunRef]:
    encoded_branch = quote(branch, safe="")
    encoded_workflow = quote(workflow_file, safe="")
    payload = _gh_api_json(
        f"repos/{repo}/actions/workflows/{encoded_workflow}/runs"
        f"?branch={encoded_branch}&status=completed&per_page=20"
    )
    raw_runs = payload.get("workflow_runs")
    if not isinstance(raw_runs, list):
        return []
    runs: list[WorkflowRunRef] = []
    for raw_run in raw_runs:
        run_ref = _workflow_run_from_payload(raw_run)
        if run_ref is not None:
            runs.append(run_ref)
    return runs


def _workflow_run_from_payload(raw_run: object) -> WorkflowRunRef | None:
    if not isinstance(raw_run, dict) or raw_run.get("conclusion") != "success":
        return None
    run_id = raw_run.get("id")
    head_branch = raw_run.get("head_branch")
    head_sha = raw_run.get("head_sha")
    html_url = raw_run.get("html_url")
    valid_payload = (
        isinstance(run_id, int)
        and isinstance(head_branch, str)
        and bool(head_branch)
        and isinstance(head_sha, str)
        and bool(head_sha)
        and isinstance(html_url, str)
        and bool(html_url)
    )
    if not valid_payload:
        return None
    return WorkflowRunRef(
        run_id=run_id,
        head_branch=head_branch,
        head_sha=head_sha,
        html_url=html_url,
    )


def _select_snapshot_artifact(*, repo: str, run_id: int) -> ArtifactRef:
    payload = _gh_api_json(f"repos/{repo}/actions/runs/{run_id}/artifacts")
    raw_artifacts = payload.get("artifacts")
    if not isinstance(raw_artifacts, list):
        msg = f"Workflow run {run_id} did not return an artifacts list."
        raise TypeError(msg)
    artifacts: list[ArtifactRef] = []
    for raw_artifact in raw_artifacts:
        if not isinstance(raw_artifact, dict):
            continue
        if raw_artifact.get("expired") is True:
            continue
        artifact_id = raw_artifact.get("id")
        name = raw_artifact.get("name")
        digest = raw_artifact.get("digest")
        if not isinstance(artifact_id, int):
            continue
        if not isinstance(name, str) or not name.startswith(_ARTIFACT_PREFIX):
            continue
        artifacts.append(
            ArtifactRef(
                artifact_id=artifact_id,
                name=name,
                digest=digest if isinstance(digest, str) else None,
            )
        )
    if not artifacts:
        msg = f"Workflow run {run_id} has no non-expired {_ARTIFACT_PREFIX} artifact."
        raise RuntimeError(msg)
    return artifacts[0]


def _download_snapshot_artifact(
    *,
    repo: str,
    run_id: int,
    artifact_name: str,
    destination: Path,
) -> None:
    _run_command(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "--repo",
            repo,
            "--name",
            artifact_name,
            "--dir",
            str(destination),
        ]
    )


def _resolve_downloaded_snapshot(download_root: Path) -> tuple[Path, Path, str]:
    artifact_paths = sorted(download_root.rglob("postgres.dump"))
    manifest_paths = sorted(download_root.rglob("manifest.json"))
    if len(artifact_paths) != 1:
        msg = (
            "Expected exactly one postgres.dump in the downloaded artifact, "
            f"found {len(artifact_paths)} under {download_root}."
        )
        raise RuntimeError(msg)
    if len(manifest_paths) != 1:
        msg = (
            "Expected exactly one manifest.json in the downloaded artifact, "
            f"found {len(manifest_paths)} under {download_root}."
        )
        raise RuntimeError(msg)
    manifest_path = manifest_paths[0].resolve()
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot_version = manifest_payload.get("snapshot_version")
    if not isinstance(snapshot_version, str) or not snapshot_version:
        msg = f"Manifest does not include a snapshot_version: {manifest_path}"
        raise RuntimeError(msg)
    return artifact_paths[0].resolve(), manifest_path, snapshot_version


def _write_latest_snapshot_metadata(
    *,
    output_root: Path,
    repo: str,
    default_branch: str,
    run_ref: WorkflowRunRef,
    artifact: ArtifactRef,
    artifact_path: Path,
    manifest_path: Path,
    snapshot_version: str,
    used_default_branch_fallback: bool,
) -> Path:
    latest_payload = {
        "artifact_name": artifact.name,
        "artifact_path": str(artifact_path),
        "default_branch": default_branch,
        "downloaded_at": datetime.now(tz=UTC).isoformat(),
        "head_branch": run_ref.head_branch,
        "head_sha": run_ref.head_sha,
        "manifest_path": str(manifest_path),
        "repo": repo,
        "snapshot_version": snapshot_version,
        "source_kind": "github_actions_artifact",
        "used_default_branch_fallback": used_default_branch_fallback,
        "workflow_run_id": run_ref.run_id,
        "workflow_run_url": run_ref.html_url,
    }
    latest_path = output_root / _LATEST_FILENAME
    latest_path.write_text(
        json.dumps(latest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return latest_path


def _git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        [_command_path("git"), "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = stderr or f"git {' '.join(args)} failed with exit code {result.returncode}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _gh_api_json(endpoint: str) -> dict[str, object]:
    output = _run_command(["gh", "api", endpoint])
    payload = json.loads(output)
    if not isinstance(payload, dict):
        msg = f"Expected a JSON object from `gh api {endpoint}`."
        raise TypeError(msg)
    return payload


def _run_command(command: list[str]) -> str:
    resolved_command = [*_resolve_command_prefix(command[:1]), *command[1:]]
    result = subprocess.run(  # noqa: S603
        resolved_command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"exit code {result.returncode}"
        msg = f"Command failed: {' '.join(resolved_command)}: {details}"
        raise RuntimeError(msg)
    return result.stdout


def _resolve_command_prefix(prefix: list[str]) -> list[str]:
    if not prefix:
        msg = "Command prefix cannot be empty."
        raise ValueError(msg)
    return [_command_path(prefix[0])]


def _command_path(command_name: str) -> str:
    resolved_path = which(command_name)
    if resolved_path is None:
        msg = f"Required executable is not on PATH: {command_name}"
        raise RuntimeError(msg)
    return resolved_path


if __name__ == "__main__":
    main()
