# Multi-Agent Worktree Workflow

## Agent Quick Start

Use one command for mutating implementation work:

```bash
make agent-start SLOT=7 ISSUE=tal_maria_ikea-123
# or
make agent-start SLOT=7 QUERY="floor plan intake"
```

This command creates an isolated worktree, claims the selected bead, bootstraps runtime files, and writes per-worktree environment settings.

## Rules

- Mutating work runs in a dedicated worktree.
- Worktree scope is per epic/major task branch.
- Keep runtime writable files isolated per worktree.
- Use explicit backend/UI ports from slot mapping:
  - backend: `8100 + slot`
  - UI: `3100 + slot`

## Runtime Isolation

Per-worktree writable paths:

- `DUCKDB_PATH=.tmp_untracked/runtime/ikea.duckdb`
- `MILVUS_LITE_URI=.tmp_untracked/runtime/milvus_lite.db`
- `ARTIFACT_ROOT_DIR=.tmp_untracked/artifacts`
- `FEEDBACK_ROOT_DIR=.tmp_untracked/comments`

Canonical dataset under `data/parquet` remains shared read-only.

## Lifecycle Checklist

1. Claim task/epic in beads (`bd update <id> --status in_progress --json`).
2. Start worktree via `make agent-start ...`.
3. Execute all related implementation in that worktree branch.
4. Run `make tidy` before completion.
5. Commit task-scoped changes.
6. Queue merge under `awaiting-merge` as `merge-request` (blocked, assigned to `merger-agent`).
7. Retire worktree after merge verification.
