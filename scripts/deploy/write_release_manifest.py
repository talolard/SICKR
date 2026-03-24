"""Write one machine-readable release manifest for deploy automation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ImageManifest:
    """Pinned release metadata for one deployable image."""

    repository: str
    version_tag: str
    commit_tag: str
    digest: str
    image_ref: str
    digest_ref: str


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    """Top-level release record shared between publish and deploy automation."""

    schema_version: int
    app_version: str
    git_tag: str
    git_sha: str
    ui_image: ImageManifest
    backend_image: ImageManifest


def _validate_app_version(app_version: str) -> str:
    if not _SEMVER_RE.fullmatch(app_version):
        msg = f"Expected plain semver for app_version, found {app_version!r}."
        raise ValueError(msg)
    return app_version


def _validate_git_tag(app_version: str, git_tag: str) -> str:
    expected_tag = f"v{app_version}"
    if git_tag != expected_tag:
        msg = f"Expected git_tag {expected_tag!r}, found {git_tag!r}."
        raise ValueError(msg)
    return git_tag


def _validate_git_sha(git_sha: str) -> str:
    normalized_sha = git_sha.lower()
    if not _SHA_RE.fullmatch(normalized_sha):
        msg = f"Expected 7-40 lowercase hex characters for git_sha, found {git_sha!r}."
        raise ValueError(msg)
    return normalized_sha


def _validate_digest(digest: str) -> str:
    normalized_digest = digest.lower()
    if not _DIGEST_RE.fullmatch(normalized_digest):
        msg = f"Expected OCI sha256 digest, found {digest!r}."
        raise ValueError(msg)
    return normalized_digest


def _build_image_manifest(
    *,
    repository: str,
    app_version: str,
    git_sha: str,
    digest: str,
) -> ImageManifest:
    version_tag = f"v{app_version}"
    commit_tag = f"sha-{git_sha}"
    return ImageManifest(
        repository=repository,
        version_tag=version_tag,
        commit_tag=commit_tag,
        digest=digest,
        image_ref=f"{repository}:{version_tag}",
        digest_ref=f"{repository}@{digest}",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write one deploy release manifest.")
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--git-tag", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--ui-repository", required=True)
    parser.add_argument("--ui-digest", required=True)
    parser.add_argument("--backend-repository", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Write the validated release manifest to disk."""

    args = _parse_args()
    app_version = _validate_app_version(args.app_version)
    git_tag = _validate_git_tag(app_version, args.git_tag)
    git_sha = _validate_git_sha(args.git_sha)
    ui_digest = _validate_digest(args.ui_digest)
    backend_digest = _validate_digest(args.backend_digest)

    manifest = ReleaseManifest(
        schema_version=1,
        app_version=app_version,
        git_tag=git_tag,
        git_sha=git_sha,
        ui_image=_build_image_manifest(
            repository=args.ui_repository,
            app_version=app_version,
            git_sha=git_sha,
            digest=ui_digest,
        ),
        backend_image=_build_image_manifest(
            repository=args.backend_repository,
            app_version=app_version,
            git_sha=git_sha,
            digest=backend_digest,
        ),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
