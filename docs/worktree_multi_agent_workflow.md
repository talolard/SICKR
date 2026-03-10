# Multi-Agent Worktree Workflow

This runbook defines how agents should work concurrently without interfering with each other.

## Goals

- Isolate git mutations per agent.
- Keep runtime data available in every worktree.
- Avoid shared writable DuckDB/Milvus lock conflicts.
- Avoid backend/UI port collisions.
- Keep merge handoff visible in beads.

## Worktree Policy

- Use worktrees for mutating tasks.
- Skip worktrees for read-only work (planning, retrospectives, code reading).
- Always create/remove with `bd worktree`:
  - `bd worktree create <path> --branch <branch>`
  - `bd worktree remove <path>`
- Worktree is per epic, not per task.
- Branch is per epic, not per task.
- All tasks for a single epic are completed in that epic worktree/branch.
- Default worktree root:
  - `${TMPDIR%/}/tal_maria_ikea-worktrees`

## Naming

- Worktree path suffix: `<epic-id>-<slug>`
- Branch: `epic/<epic-id>-<slug>`

## Commit Policy Inside Epic Worktree

- Default: one commit per task.
- Feedback iterations may add feedback commits on the same epic branch.
- Keep commits task-scoped; do not combine unrelated task changes in one commit.

Example:

```bash
bd worktree create "${TMPDIR%/}/tal_maria_ikea-worktrees/tal_maria_ikea-abc-search-fix" \
  --branch "epic/tal_maria_ikea-abc-search-fix"
```

## Bootstrap Every Worktree

Run inside the target worktree:

```bash
uv sync --all-groups
make ui-install
```

Or use the helper, which does both and sets up isolated runtime files:

```bash
scripts/worktree/bootstrap.sh --slot <0-99>
```

Set isolated runtime paths (stored in `.tmp_untracked/worktree.env` by helper scripts):

- `DUCKDB_PATH=.tmp_untracked/runtime/ikea.duckdb`
- `MILVUS_LITE_URI=.tmp_untracked/runtime/milvus_lite.db`
- `ARTIFACT_ROOT_DIR=.tmp_untracked/artifacts`
- `FEEDBACK_ROOT_DIR=.tmp_untracked/comments`

Data policy:

- `data/parquet` remains shared read-only static source.
- Each worktree gets its own writable DuckDB and Milvus file copy.
- Do not run multiple agents against the same writable DB file.

## Port Policy

Every agent must use explicit ports.

- Backend: `8100-8199`
- UI: `3100-3199`
- Slot `N` mapping:
  - backend `8100 + N`
  - UI `3100 + N`

Example (`slot=7`):

```bash
make chat PORT=8107
make ui-dev-real UI_PORT=3107 PY_AG_UI_URL=http://127.0.0.1:8107/ag-ui/
```

## Standard Scripted Flow

From canonical repo root:

```bash
scripts/worktree/new.sh --epic tal_maria_ikea-abc --slug search-fix --slot 7
```

Inside the worktree:

```bash
scripts/worktree/run-dev.sh
```

When done:

```bash
scripts/worktree/retire.sh --worktree "${TMPDIR%/}/tal_maria_ikea-worktrees/tal_maria_ikea-abc-search-fix"
```

## Epic Lifecycle Checklist

1. Claim epic: `bd update <epic-id> --status in_progress --json`.
2. Create one epic-scoped worktree/branch.
3. Bootstrap environment and isolated runtime files once.
4. Complete all epic tasks in that same worktree/branch.
5. Keep one commit per task; use feedback commits only for review follow-up.
6. Run `make tidy` before declaring implementation complete.
7. Queue merge using a `merge-request` child under `awaiting-merge`.
8. After merge, close queue item + epic and remove worktree.

## Merge Queue Policy

- Use the persistent beads epic: `awaiting-merge`.
- For each implementation-complete epic awaiting merge, create a child issue of type `merge-request`.

### merge-request Required Fields

- Branch: source branch name.
- PR: URL or PR number.
- Base: merge target branch.
- CI: latest status summary.
- Risk: deployment/rollback notes.

### Suggested Creation Command

```bash
bd create "Merge <epic-id>: <summary>" \
  -t merge-request \
  -p 1 \
  --deps "parent-child:tal_maria_ikea-0uk" \
  --description $'Context:\nReady to merge.\n\nDefinition of done:\n- Merged to target branch.\n- Post-merge checks confirmed.\n\nBranch:\nPR:\nBase:\nCI:\nRisk/Rollback:' \
  --json
```

`tal_maria_ikea-0uk` is the current `awaiting-merge` epic.

## Troubleshooting

### DuckDB lock errors

- Confirm worktree env points to local `.tmp_untracked/runtime/ikea.duckdb`.
- Re-copy canonical DB into worktree runtime path with `scripts/worktree/bootstrap.sh --force-db-refresh`.

### Milvus lock or stale file errors

- Ensure each worktree has unique `.tmp_untracked/runtime/milvus_lite.db`.
- Remove stale `.lock` files only in the local worktree runtime dir.

### Port already in use

- Run `lsof -iTCP:<port> -sTCP:LISTEN`.
- Pick another slot or stop the conflicting process.
- `scripts/worktree/run-dev.sh` fails fast when configured ports are occupied.
