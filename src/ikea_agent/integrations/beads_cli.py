"""Helpers for creating Beads issues from runtime workflows."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BeadsTraceIssueResult:
    """Created Beads issue ids for one trace report."""

    epic_id: str
    task_id: str


class BeadsTraceIssueCreator:
    """Create trace-triage Beads issues from a local repo checkout."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = _resolve_beads_repo_root(repo_root)

    def create_trace_epic_and_task(
        self,
        *,
        title: str,
        description: str | None,
        trace_directory: str,
        trace_json_path: str,
        thread_id: str,
        agent_name: str,
    ) -> BeadsTraceIssueResult:
        """Create one epic plus one triage child task for a saved trace."""

        issue_description = _build_trace_issue_description(
            description=description,
            trace_directory=trace_directory,
            trace_json_path=trace_json_path,
            thread_id=thread_id,
            agent_name=agent_name,
        )
        epic_id = self._create_issue(
            issue_type="epic",
            priority="1",
            title=title,
            description=issue_description,
        )
        task_id = self._create_issue(
            issue_type="task",
            priority="1",
            parent=epic_id,
            title=f"Analyze saved trace: {title}",
            description=issue_description,
        )
        return BeadsTraceIssueResult(epic_id=epic_id, task_id=task_id)

    def _create_issue(
        self,
        *,
        issue_type: str,
        priority: str,
        title: str,
        description: str,
        parent: str | None = None,
    ) -> str:
        command = _build_bd_create_command(
            issue_type=issue_type,
            priority=priority,
            title=title,
            description=description,
            parent=parent,
        )
        completed = subprocess.run(  # noqa: S603
            command,
            check=True,
            cwd=self._repo_root,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        issue_id = payload.get("id")
        if not isinstance(issue_id, str) or not issue_id:
            msg = "Beads create did not return an issue id."
            raise RuntimeError(msg)
        return issue_id


def _build_trace_issue_description(
    *,
    description: str | None,
    trace_directory: str,
    trace_json_path: str,
    thread_id: str,
    agent_name: str,
) -> str:
    detail_lines = [
        "Context:",
        "A developer saved a runtime trace from the application UI for investigation.",
        "",
        f"Thread: `{thread_id}`",
        f"Agent: `{agent_name}`",
        f"Trace directory: `{trace_directory}`",
        f"Trace JSON: `{trace_json_path}`",
    ]
    if description:
        detail_lines.extend(["", "Description:", description])
    detail_lines.extend(
        [
            "",
            "Definition of done:",
            (
                "- Review the saved trace bundle and identify the user-visible issue "
                "or runtime behavior."
            ),
            "- Summarize the likely root cause and next action.",
            "- Link any follow-up implementation bead(s).",
        ]
    )
    return "\n".join(detail_lines)


def _build_bd_create_command(
    *,
    issue_type: str,
    priority: str,
    title: str,
    description: str,
    parent: str | None,
) -> list[str]:
    command = [
        "bd",
        "create",
        "--json",
        "--type",
        issue_type,
        "--priority",
        priority,
        "--title",
        title,
        "--description",
        description,
    ]
    if parent is not None:
        command.extend(["--parent", parent])
    return command


def _resolve_beads_repo_root(start_dir: Path) -> Path:
    repo_root = start_dir.resolve()
    redirect_path = repo_root / ".beads" / "redirect"
    if not redirect_path.exists():
        return repo_root
    redirect_target = (
        redirect_path.parent / redirect_path.read_text(encoding="utf-8").strip()
    ).resolve(strict=False)
    resolved = redirect_target.parent if redirect_target.name == ".beads" else redirect_target
    if resolved.exists():
        return resolved
    resolved_text = str(resolved)
    if resolved_text.startswith("/private/Users/"):
        adjusted = Path(resolved_text.removeprefix("/private"))
        if adjusted.exists():
            return adjusted
    return repo_root
