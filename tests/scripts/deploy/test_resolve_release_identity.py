from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deploy.resolve_release_identity import (
    main as resolve_release_identity_main,
)
from scripts.deploy.resolve_release_identity import (
    resolve_release_identity,
)


def _write_release_event(
    path: Path,
    *,
    title: str = "chore(release): release 1.4.2",
    head_ref: str = "release-please--branches--release",
    merged: bool = True,
    merge_commit_sha: str = "abc1234def5678",
    base_ref: str = "release",
) -> None:
    path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "merged": merged,
                    "title": title,
                    "merge_commit_sha": merge_commit_sha,
                    "base": {"ref": base_ref},
                    "head": {"ref": head_ref},
                }
            }
        ),
        encoding="utf-8",
    )


def test_resolve_release_identity_accepts_release_please_merge(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(event_path)

    identity = resolve_release_identity(
        event_path=event_path,
        version_file=version_file,
        head_sha="abc1234def5678",
    )

    assert identity.version == "1.4.2"
    assert identity.git_tag == "v1.4.2"
    assert identity.git_sha == "abc1234def5678"


def test_resolve_release_identity_accepts_plain_release_title(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(event_path, title="chore(release): release 1.4.2")

    identity = resolve_release_identity(
        event_path=event_path,
        version_file=version_file,
        head_sha="abc1234def5678",
    )

    assert identity.git_tag == "v1.4.2"


def test_resolve_release_identity_ignores_release_pr_title_text(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(
        event_path,
        title="release please wrote some other title here",
        head_ref="release-please--branches--release--components--designagent",
    )

    identity = resolve_release_identity(
        event_path=event_path,
        version_file=version_file,
        head_sha="abc1234def5678",
    )

    assert identity.git_tag == "v1.4.2"


def test_resolve_release_identity_rejects_non_release_please_head_ref(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(event_path, head_ref="feature/not-a-release-pr")

    with pytest.raises(ValueError, match="Release Please head-ref shape"):
        resolve_release_identity(
            event_path=event_path,
            version_file=version_file,
            head_sha="abc1234def5678",
        )


def test_resolve_release_identity_main_prints_github_output_lines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(event_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "resolve_release_identity.py",
            "--event-path",
            str(event_path),
            "--version-file",
            str(version_file),
            "--head-sha",
            "abc1234def5678",
        ],
    )

    assert resolve_release_identity_main() == 0

    assert capsys.readouterr().out.splitlines() == [
        "version=1.4.2",
        "tag=v1.4.2",
        "git_sha=abc1234def5678",
    ]
