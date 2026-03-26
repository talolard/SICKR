"""Resolve one publishable release identity from the merged Release Please PR.

This keeps the publish workflow anchored to the merged release commit and the
checked-in release version instead of trusting mutable pull request title text.
The release version comes from `version.txt`, and this helper proves that the
merged release PR, current checked-out commit, and final Git tag all describe
the same release.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.deploy.read_release_version import read_release_version
from scripts.deploy.release_manifest import validate_app_version, validate_git_sha

_RELEASE_PLEASE_HEAD_REF_PREFIX = "release-please--branches--release"


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    """One validated release identity shared across workflow publication steps."""

    version: str
    git_tag: str
    git_sha: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def _resolve_current_head_sha(head_sha: str | None) -> str:
    if head_sha is not None:
        return validate_git_sha(head_sha)
    git_executable = shutil.which("git")
    if git_executable is None:
        msg = "Could not locate git in PATH while resolving the checked-out release commit."
        raise RuntimeError(msg)
    resolved_sha = subprocess.check_output(  # noqa: S603
        [git_executable, "rev-parse", "HEAD"],
        text=True,
    ).strip()
    return validate_git_sha(resolved_sha)


def resolve_release_identity(
    *,
    event_path: Path,
    version_file: Path,
    head_sha: str | None = None,
) -> ReleaseIdentity:
    """Validate one merged Release Please PR against the checked-out release commit."""

    payload = _read_json_object(event_path)
    pull_request = _require_object(payload, "pull_request")

    if pull_request.get("merged") is not True:
        msg = "Release publication requires a merged pull request event."
        raise ValueError(msg)

    base = _require_object(pull_request, "base")
    base_ref = _require_string(base, "ref")
    if base_ref != "release":
        msg = f"Release publication only runs from the release branch, found base ref {base_ref!r}."
        raise ValueError(msg)

    head = _require_object(pull_request, "head")
    head_ref = _require_string(head, "ref")
    if not head_ref.startswith(_RELEASE_PLEASE_HEAD_REF_PREFIX):
        msg = f"Release publication requires a Release Please head-ref shape, found {head_ref!r}."
        raise ValueError(msg)

    version = validate_app_version(read_release_version(version_file))

    merge_commit_sha = validate_git_sha(_require_string(pull_request, "merge_commit_sha"))
    current_head_sha = _resolve_current_head_sha(head_sha)
    if merge_commit_sha != current_head_sha:
        msg = (
            "Checked-out commit does not match merged release PR commit: "
            f"{current_head_sha!r} != {merge_commit_sha!r}."
        )
        raise ValueError(msg)

    return ReleaseIdentity(
        version=version,
        git_tag=f"v{version}",
        git_sha=current_head_sha,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve the publishable release identity from a merged Release Please PR."
    )
    parser.add_argument(
        "--event-path",
        type=Path,
        default=None,
        help="Path to the GitHub Actions event payload JSON.",
    )
    parser.add_argument(
        "--version-file",
        type=Path,
        default=_repo_root() / "version.txt",
        help="Path to the plain semver release version file.",
    )
    parser.add_argument(
        "--head-sha",
        help="Optional checked-out commit SHA override for tests.",
    )
    return parser.parse_args()


def main() -> int:
    """Print the validated release identity as GitHub Actions output lines."""

    args = _parse_args()
    event_path = args.event_path
    if event_path is None:
        github_event_path = os.environ.get("GITHUB_EVENT_PATH")
        if github_event_path is None:
            msg = "GITHUB_EVENT_PATH must be set unless --event-path is provided."
            raise RuntimeError(msg)
        event_path = Path(github_event_path)
    release = resolve_release_identity(
        event_path=event_path,
        version_file=args.version_file,
        head_sha=args.head_sha,
    )
    print(f"version={release.version}")
    print(f"tag={release.git_tag}")
    print(f"git_sha={release.git_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
