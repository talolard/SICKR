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
    action: str = "published",
    tag_name: str = "v1.4.2",
) -> None:
    path.write_text(
        json.dumps(
            {
                "action": action,
                "release": {"tag_name": tag_name},
            }
        ),
        encoding="utf-8",
    )


def test_resolve_release_identity_accepts_published_release(tmp_path: Path) -> None:
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


def test_resolve_release_identity_rejects_non_published_event(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(event_path, action="created")

    with pytest.raises(ValueError, match="published release event"):
        resolve_release_identity(
            event_path=event_path,
            version_file=version_file,
            head_sha="abc1234def5678",
        )


def test_resolve_release_identity_rejects_mismatched_release_tag(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.4.2\n", encoding="utf-8")
    _write_release_event(event_path, tag_name="v9.9.9")

    with pytest.raises(ValueError, match=r"does not match version.txt tag"):
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
