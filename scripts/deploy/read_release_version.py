"""Read and validate the release version from the repo-root version file."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_release_version(version_file: Path) -> str:
    """Return the normalized release version from one version file."""

    version = version_file.read_text(encoding="utf-8").strip()
    if not _SEMVER_RE.fullmatch(version):
        msg = f"Expected plain semver in {version_file}, found {version!r}."
        raise ValueError(msg)
    return version


def main() -> int:
    """Print the validated release version for workflows and scripts."""

    parser = argparse.ArgumentParser(description="Read the release version from version.txt.")
    parser.add_argument(
        "--version-file",
        type=Path,
        default=_repo_root() / "version.txt",
        help="Path to the plain semver version file.",
    )
    parser.add_argument(
        "--with-v-prefix",
        action="store_true",
        help="Print the version with a leading v for Git tag use.",
    )
    args = parser.parse_args()

    version = read_release_version(args.version_file)
    print(f"v{version}" if args.with_v_prefix else version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
