from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from scripts.deploy.release_branch_governance import (
    validate_release_pull_request,
    validate_release_push,
)


def _git(repo_root: Path, *args: str) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        msg = "git must be installed for release-branch governance tests."
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603
        [git_executable, *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_release_pr_event(path: Path, *, head_ref: str, title: str) -> None:
    _write_json(
        path,
        {
            "pull_request": {
                "base": {"ref": "release"},
                "head": {"ref": head_ref},
                "title": title,
            }
        },
    )


def _write_release_push_event(path: Path, *, before_sha: str, after_sha: str) -> None:
    _write_json(
        path,
        {
            "ref": "refs/heads/release",
            "before": before_sha,
            "after": after_sha,
        },
    )


def _init_repo(repo_root: Path) -> tuple[str, str]:
    _git(repo_root, "init", "--initial-branch=main")
    _git(repo_root, "config", "user.name", "Test User")
    _git(repo_root, "config", "user.email", "test@example.com")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo_root, "add", "README.md")
    _git(repo_root, "commit", "-m", "feat(repo): seed repo")
    _git(repo_root, "branch", "release")
    main_sha = _git(repo_root, "rev-parse", "main")
    release_sha = _git(repo_root, "rev-parse", "release")
    _git(repo_root, "update-ref", "refs/remotes/origin/main", main_sha)
    _git(repo_root, "update-ref", "refs/remotes/origin/release", release_sha)
    return main_sha, release_sha


def test_validate_release_pull_request_accepts_main_promotion(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    _write_release_pr_event(
        event_path,
        head_ref="main",
        title="feat(deploy): merge main into release",
    )

    validate_release_pull_request(event_path=event_path)


def test_validate_release_pull_request_accepts_release_please_pr(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    _write_release_pr_event(
        event_path,
        head_ref="release-please--branches--release",
        title="chore(release): release 0.4.0",
    )

    validate_release_pull_request(event_path=event_path)


def test_validate_release_pull_request_rejects_feature_branch(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    _write_release_pr_event(
        event_path,
        head_ref="feature/direct-release-hotfix",
        title="fix(deploy): hotfix release directly",
    )

    with pytest.raises(ValueError, match="must come from main promotion"):
        validate_release_pull_request(event_path=event_path)


def test_validate_release_push_accepts_release_please_metadata_commit(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _, release_before = _init_repo(repo_root)
    _git(repo_root, "checkout", "release")
    (repo_root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (repo_root / "version.txt").write_text("0.4.0\n", encoding="utf-8")
    (repo_root / ".release-please-manifest.json").write_text('{".":"0.4.0"}\n', encoding="utf-8")
    _git(repo_root, "add", "CHANGELOG.md", "version.txt", ".release-please-manifest.json")
    _git(repo_root, "commit", "-m", "chore(release): release 0.4.0")
    release_after = _git(repo_root, "rev-parse", "HEAD")

    event_path = tmp_path / "push.json"
    _write_release_push_event(event_path, before_sha=release_before, after_sha=release_after)

    validate_release_push(event_path=event_path, repo_root=repo_root)


def test_validate_release_push_accepts_merge_from_main(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _, release_before = _init_repo(repo_root)

    _git(repo_root, "checkout", "main")
    (repo_root / "feature.txt").write_text("promote me\n", encoding="utf-8")
    _git(repo_root, "add", "feature.txt")
    _git(repo_root, "commit", "-m", "fix(deploy): prepare main promotion")
    main_after = _git(repo_root, "rev-parse", "HEAD")
    _git(repo_root, "update-ref", "refs/remotes/origin/main", main_after)

    _git(repo_root, "checkout", "release")
    _git(repo_root, "merge", "--no-ff", "main", "-m", "Merge main into release")
    release_after = _git(repo_root, "rev-parse", "HEAD")

    event_path = tmp_path / "push.json"
    _write_release_push_event(event_path, before_sha=release_before, after_sha=release_after)

    validate_release_push(event_path=event_path, repo_root=repo_root)


def test_validate_release_push_rejects_direct_release_hotfix(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _, release_before = _init_repo(repo_root)

    _git(repo_root, "checkout", "release")
    (repo_root / "hotfix.txt").write_text("oops\n", encoding="utf-8")
    _git(repo_root, "add", "hotfix.txt")
    _git(repo_root, "commit", "-m", "fix(deploy): hotfix release directly")
    release_after = _git(repo_root, "rev-parse", "HEAD")

    event_path = tmp_path / "push.json"
    _write_release_push_event(event_path, before_sha=release_before, after_sha=release_after)

    with pytest.raises(
        ValueError,
        match=(
            "neither a Release Please metadata commit nor a history-preserving promotion from main"
        ),
    ):
        validate_release_push(event_path=event_path, repo_root=repo_root)
