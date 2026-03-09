from __future__ import annotations

import json
from pathlib import Path

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from ikea_agent.chat.subagents.cli import _read_input_payload, main
from ikea_agent.chat.subagents.registry import SubagentRegistration


async def _fake_run(raw_input: str) -> dict[str, object]:
    return {"echo": raw_input}


def test_read_input_payload_prefers_inline_text() -> None:
    assert _read_input_payload("hello", None) == "hello"


def test_read_input_payload_from_file(tmp_path: Path) -> None:
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text("from-file", encoding="utf-8")

    assert _read_input_payload(None, str(payload_path)) == "from-file"


def test_read_input_payload_rejects_both_inputs() -> None:
    with pytest.raises(ValueError, match="only one"):
        _ = _read_input_payload("inline", "payload.txt")


def test_cli_main_success(monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "ikea_agent.chat.subagents.cli.get_subagent",
        lambda name: SubagentRegistration(name=name, description="test", run=_fake_run),
    )

    code = main(["--agent", "floor_plan_intake", "--input", "hello"])
    stdout = capsys.readouterr().out.strip()

    assert code == 0
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert payload["output"]["echo"] == "hello"


def test_cli_main_error(monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    def _raise(_: str) -> SubagentRegistration:
        raise KeyError("missing")

    monkeypatch.setattr("ikea_agent.chat.subagents.cli.get_subagent", _raise)

    code = main(["--agent", "unknown", "--input", "hello"])
    stderr = capsys.readouterr().err.strip()

    assert code == 1
    payload = json.loads(stderr)
    assert payload["ok"] is False
