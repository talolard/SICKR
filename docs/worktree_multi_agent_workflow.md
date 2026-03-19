# Multi-Agent Worktree Workflow

## Agent Quick Start

Use one command for mutating implementation work:

```bash
make agent-start SLOT=7 ISSUE=tal_maria_ikea-123
# or
make agent-start SLOT=7 QUERY="floor plan intake"
```

This command creates an isolated worktree, claims the selected bead, bootstraps runtime files, and writes per-worktree environment settings.

After bootstrap:

- plain `make` targets automatically load `.tmp_untracked/worktree.env`
- slot claims are rejected if another worktree or running process is already using that slot's ports
- bootstrap ensures the shared Milvus dependency and the slot-scoped Postgres dependency are prepared before dev servers start

## Rules

- Mutating work runs in a dedicated worktree.
- Worktree scope is per epic/major task branch.
- Keep runtime writable files isolated per worktree.
- `.beads/issues.jsonl` and `.beads/interactions.jsonl` belong to the dedicated `beads` sync branch, not normal feature branches.
- Use explicit backend/UI ports from slot mapping:
  - backend: `8100 + slot`
  - UI: `3100 + slot`

## Runtime Isolation

Per-worktree writable paths:

- `DATABASE_URL=postgresql+psycopg://ikea:ikea@127.0.0.1:1543x/ikea_agent`
- `MILVUS_URI=http://127.0.0.1:19530`
- `ARTIFACT_ROOT_DIR=.tmp_untracked/artifacts`
- `FEEDBACK_ROOT_DIR=.tmp_untracked/comments`
- `TRACE_ROOT_DIR=.tmp_untracked/traces`

Dependency scopes:

- one global Milvus Docker volume and service shared by all worktrees
- one worktree-local Postgres Docker volume and service per slot
- canonical catalog parquet under `data/parquet` remains shared read-only

## Lifecycle Checklist

1. Claim task/epic in beads (`bd update <id> --status in_progress --json`).
2. Start worktree via `make agent-start ...`.
3. Execute all related implementation in that worktree branch.
4. Use `make deps-status SLOT=<slot>` or `scripts/worktree/deps.sh status --slot <slot>` when dependency diagnostics are needed.
5. Run `make tidy` before completion. In this repo that covers backend Ruff/Pyrefly/Pytest plus frontend ESLint/TypeScript/Vitest; run `make ui-test-e2e-real-ui-smoke` separately when the change touches runtime/UI behavior.
6. Commit task-scoped changes.
7. Queue merge under `awaiting-merge` as `merge-request` (blocked, assigned to `merger-agent`).
8. Retire worktree after merge verification.

## Beads Sync Branch Recovery

If a stale local branch stages `.beads/issues.jsonl` or `.beads/interactions.jsonl`, the pre-commit hook now blocks the commit outside the `beads` branch.

Recovery flow:

1. Unstage the Beads JSONL files with `git restore --staged .beads/issues.jsonl .beads/interactions.jsonl`.
2. Rebase or merge the latest `origin/main` so the sync-branch policy and ignores are present locally.
3. Recommit your feature work without the Beads JSONL files.
4. Use the dedicated `beads` branch for explicit Beads sync work.
