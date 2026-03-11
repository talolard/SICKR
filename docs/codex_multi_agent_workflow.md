# Codex multi-agent workflow

This repo now keeps its Codex multi-agent workflow in project-local config and prompt files.
The design/spec documents remain under `plans/agents/`, while the executable role system lives under `.codex/`.

## File layout

- `.codex/config.toml`: project-local role registry
- `.codex/agents/<role>/config.<role>.toml`: per-role config files
- `.codex/agents/<role>/prompt.<role>.md`: per-role behavioral prompts
- `.codex/prompt_support/*.md`: reusable support guidance shared by multiple prompts
- `plans/agents/`: design history, lessons, and the implementation epic

## Roles

- `default`: top-level coordinator for the session
- `spec_planner`: specification and requirement-shaping role
- `epic_writer`: Beads graph and task-structure role
- `epic_worker`: epic implementation and readiness owner
- `worker`: small-task implementation role
- `repo_explorer`: read-only codebase navigator
- `docs_researcher`: read-only documentation researcher
- `pr_reviewer`: independent review pass
- `merge_coordinator`: serialized merge and cleanup owner

## Policy split

`AGENTS.md` stays the source of truth for repo-wide invariants: validation gates, typing rules, runtime conventions, Beads usage, merge queue rules, and git identity.

Role-specific behavior lives in `.codex/agents/<role>/prompt.<role>.md` so the instructions that apply only to one role do not clutter the repo-wide policy.

## Ownership model

- `epic_worker` owns implementation readiness: coding, validation, PR health, and rebasing/conflict resolution before handoff.
- `merge_coordinator` owns final serialized landing and merged-worktree cleanup.
- `worker` is intentionally for small tasks that do not need Beads overhead.

## Updating the workflow

1. Evolve the design in `plans/agents/`.
2. Review the desired changes with a human.
3. Update the executable `.codex/` role files.
4. Update `AGENTS.md` and docs if repo-wide policy changes.
