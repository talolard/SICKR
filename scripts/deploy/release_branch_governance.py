"""Validate release-branch governance for PR and push automation.

The repository cannot encode GitHub branch-protection settings in source, so
this module focuses on the checks the repo *can* own directly:

- only `main` promotion PRs and Release Please PRs should target `release`
- direct `release` pushes should be limited to history-preserving promotion
  merges from `main` or release-please metadata commits

These checks are designed to back GitHub branch rules rather than pretend YAML
alone can fully prevent an administrator or direct pusher from bypassing them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Final

RELEASE_BRANCH: Final[str] = "release"
MAIN_REMOTE_REF: Final[str] = "origin/main"
RELEASE_PLEASE_HEAD_REF_PREFIX: Final[str] = "release-please--branches--release"
MERGE_PARENT_COUNT: Final[int] = 2
RELEASE_PLEASE_FILES: Final[frozenset[str]] = frozenset(
    {
        ".release-please-manifest.json",
        "CHANGELOG.md",
        "version.txt",
    }
)
RELEASE_TITLE_RE: Final[re.Pattern[str]] = re.compile(
    r"^chore\(release\): release(?: [A-Za-z0-9][A-Za-z0-9._-]*)? "
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?: .*)?$"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_executable() -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        msg = "Could not locate git in PATH while validating release-branch governance."
        raise RuntimeError(msg)
    return git_executable


def _git_output(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(  # noqa: S603
        [_git_executable(), *args],
        cwd=repo_root,
        text=True,
    ).strip()


def _git_ok(repo_root: Path, *args: str) -> bool:
    result = subprocess.run(  # noqa: S603
        [_git_executable(), *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected JSON object in {path}."
        raise TypeError(msg)
    return payload


def _require_object(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        msg = f"Expected object field {key!r} in GitHub event payload."
        raise TypeError(msg)
    return value


def _require_string(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"Expected non-empty string field {key!r} in GitHub event payload."
        raise ValueError(msg)
    return value


def _is_release_please_head_ref(head_ref: str) -> bool:
    return head_ref.startswith(RELEASE_PLEASE_HEAD_REF_PREFIX)


def _is_release_please_title(title: str) -> bool:
    return RELEASE_TITLE_RE.fullmatch(title) is not None


def validate_release_pull_request(*, event_path: Path) -> None:
    """Allow only `main` promotion PRs and Release Please PRs into `release`."""

    payload = _read_json_object(event_path)
    pull_request = _require_object(payload, "pull_request")
    base_ref = _require_string(_require_object(pull_request, "base"), "ref")
    if base_ref != RELEASE_BRANCH:
        msg = (
            "Release governance only applies to PRs targeting "
            f"{RELEASE_BRANCH!r}, found {base_ref!r}."
        )
        raise ValueError(msg)

    head_ref = _require_string(_require_object(pull_request, "head"), "ref")
    if head_ref == "main":
        return

    if _is_release_please_head_ref(head_ref):
        title = _require_string(pull_request, "title")
        if not _is_release_please_title(title):
            msg = (
                "Release Please PRs targeting release must use the standard release title, "
                f"found {title!r}."
            )
            raise ValueError(msg)
        return

    msg = (
        "PRs targeting release must come from main promotion or a Release Please head ref, "
        f"found {head_ref!r}."
    )
    raise ValueError(msg)


def _commit_subject(repo_root: Path, commit_sha: str) -> str:
    return _git_output(repo_root, "show", "-s", "--format=%s", commit_sha)


def _commit_changed_files(repo_root: Path, commit_sha: str) -> frozenset[str]:
    output = _git_output(repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha)
    return frozenset(line for line in output.splitlines() if line)


def _commit_parents(repo_root: Path, commit_sha: str) -> list[str]:
    output = _git_output(repo_root, "show", "-s", "--format=%P", commit_sha)
    return [item for item in output.split(" ") if item]


def _commit_is_on_main(repo_root: Path, commit_sha: str, *, main_ref: str) -> bool:
    return _git_ok(repo_root, "merge-base", "--is-ancestor", commit_sha, main_ref)


def _is_release_please_commit(repo_root: Path, commit_sha: str) -> bool:
    subject = _commit_subject(repo_root, commit_sha)
    if not _is_release_please_title(subject):
        return False
    changed_files = _commit_changed_files(repo_root, commit_sha)
    return bool(changed_files) and changed_files <= RELEASE_PLEASE_FILES


def _is_main_promotion_commit(repo_root: Path, commit_sha: str, *, main_ref: str) -> bool:
    if _commit_is_on_main(repo_root, commit_sha, main_ref=main_ref):
        return True
    parents = _commit_parents(repo_root, commit_sha)
    if len(parents) < MERGE_PARENT_COUNT:
        return False
    return any(_commit_is_on_main(repo_root, parent, main_ref=main_ref) for parent in parents)


def _commit_range(repo_root: Path, before_sha: str, after_sha: str) -> list[str]:
    if before_sha == "0" * 40:
        return [after_sha]
    output = _git_output(repo_root, "rev-list", "--reverse", f"{before_sha}..{after_sha}")
    return [line for line in output.splitlines() if line]


def validate_release_push(*, event_path: Path, repo_root: Path) -> None:
    """Reject direct release-branch drift outside the allowed promotion paths."""

    payload = _read_json_object(event_path)
    ref = _require_string(payload, "ref")
    if ref != f"refs/heads/{RELEASE_BRANCH}":
        msg = f"Release governance only applies to refs/heads/{RELEASE_BRANCH}, found {ref!r}."
        raise ValueError(msg)

    before_sha = _require_string(payload, "before")
    after_sha = _require_string(payload, "after")
    for commit_sha in _commit_range(repo_root, before_sha, after_sha):
        if _is_release_please_commit(repo_root, commit_sha):
            continue
        if _is_main_promotion_commit(repo_root, commit_sha, main_ref=MAIN_REMOTE_REF):
            continue
        subject = _commit_subject(repo_root, commit_sha)
        msg = (
            "Release push introduced a commit that is neither a Release Please metadata "
            f"commit nor a history-preserving promotion from main: {commit_sha} {subject!r}."
        )
        raise ValueError(msg)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release-branch governance.")
    parser.add_argument("mode", choices=("pull-request", "push"))
    parser.add_argument(
        "--event-path",
        type=Path,
        default=None,
        help="Path to the GitHub event payload JSON.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root(),
        help="Path to the repository root for git history checks.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the requested release-governance validation mode."""

    args = _parse_args()
    event_path = args.event_path
    if event_path is None:
        github_event_path = os.environ.get("GITHUB_EVENT_PATH")
        if github_event_path is None:
            msg = "GITHUB_EVENT_PATH must be set unless --event-path is provided."
            raise RuntimeError(msg)
        event_path = Path(github_event_path)

    if args.mode == "pull-request":
        validate_release_pull_request(event_path=event_path)
    else:
        validate_release_push(event_path=event_path, repo_root=args.repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
