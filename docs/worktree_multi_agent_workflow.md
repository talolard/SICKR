# Multi-Agent Worktree Workflow

## Agent Quick Start

Use the full bootstrap for runnable implementation work:

```bash
make agent-start SLOT=7 ISSUE=tal_maria_ikea-123
# or
make agent-start SLOT=7 QUERY="floor plan intake"
```

Use the lightweight bootstrap for docs, specs, and research work that does not
need backend or UI processes:

```bash
make agent-start-docs ISSUE=tal_maria_ikea-123
# or
make agent-start-docs QUERY="bootstrap docs"
```

The full command creates an isolated worktree, claims the selected bead,
bootstraps runtime files, and writes per-worktree environment settings.

The docs command creates the worktree and writes a minimal worktree env file,
but does not claim a slot or prepare runtime dependencies.

After bootstrap:

- plain `make` targets automatically load `.tmp_untracked/worktree.env`
- full bootstrap slot claims are rejected if another worktree or running process is already using that slot's ports
- full bootstrap ensures the slot-scoped Postgres dependency is prepared before dev servers start
- `make dev human` is reserved for the canonical checkout and Tal's persistent human-owned slot `90`; agents must not use it from a worktree
- docs-mode worktrees must be upgraded before runtime commands:

```bash
bash scripts/worktree/bootstrap.sh --mode full --slot 7
```

## Rules

- Mutating work runs in a dedicated worktree.
- Worktree scope is per epic/major task branch.
- Keep runtime writable files isolated per worktree.
- `.beads/issues.jsonl` and `.beads/interactions.jsonl` belong to the dedicated `beads` sync branch, not normal feature branches.
- Use explicit backend/UI ports from slot mapping for full bootstrap:
  - backend: `8100 + slot`
  - UI: `3100 + slot`

## Runtime Isolation

Per-worktree writable paths:

- `DATABASE_URL=postgresql+psycopg://ikea:ikea@127.0.0.1:1543x/ikea_agent`
- `ARTIFACT_ROOT_DIR=.tmp_untracked/artifacts`
- `FEEDBACK_ROOT_DIR=.tmp_untracked/comments`

Full-bootstrap dependency scopes:

- one worktree-local Postgres Docker volume and service per slot
- one worktree-local Postgres snapshot cache under `.tmp_untracked/docker-deps/snapshots`
- canonical catalog parquet under `data/parquet` remains shared read-only

Docs-mode worktrees do not create runtime services or claim a slot.

## Lifecycle Checklist

1. Claim task/epic in beads (`bd update <id> --status in_progress --json`).
2. Start worktree via `make agent-start ...` for runnable work, or
   `make agent-start-docs ...` for docs/research/spec work.
3. Execute all related implementation in that worktree branch.
4. If you started in docs mode and later need runtime, upgrade the same worktree
   with `bash scripts/worktree/bootstrap.sh --mode full --slot <n>`.
5. Use `make deps-status SLOT=<slot>` or `scripts/worktree/deps.sh status --slot <slot>` when dependency diagnostics are needed for full bootstrap.
6. Run `make tidy` before completion. In this repo that covers backend Ruff/Pyrefly/Pytest plus frontend ESLint/TypeScript/Vitest; the real-UI smoke now runs in deferred CI after `PR CI` and `Dependency Review` succeed for the PR SHA. Run `make ui-test-e2e-real-ui-smoke` locally only when debugging the live CopilotKit or AG-UI path.
7. Commit task-scoped changes.
8. Queue merge under `awaiting-merge` as `merge-request` (blocked, assigned to `merger-agent`).
9. Retire worktree after merge verification.

## Beads Sync Branch Recovery

If a stale local branch stages `.beads/issues.jsonl` or `.beads/interactions.jsonl`, the pre-commit hook now blocks the commit outside the `beads` branch.

Recovery flow:

1. Unstage the Beads JSONL files with `git restore --staged .beads/issues.jsonl .beads/interactions.jsonl`.
2. Rebase or merge the latest `origin/main` so the sync-branch policy and ignores are present locally.
3. Recommit your feature work without the Beads JSONL files.
4. Use the dedicated `beads` branch for explicit Beads sync work.
