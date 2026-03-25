# Worktree Bootstrap Simplification Plan

Date: 2026-03-20

Epic: `tal_maria_ikea-0ia`

## Goal

Reduce local setup cost for non-runtime work while preserving safe isolation for
runnable agent development.

The target end state is:

- one lightweight docs/research worktree-start path that does not claim a slot
  or start runtime dependencies
- one full runnable bootstrap path for implementation work
- one repo-managed Postgres service for the full path, with one isolated
  database per worktree instead of one container per worktree

## Why this is needed

The current `make agent-start` flow is optimized for "I need a runnable app
right now", not for "I need a branch to write a plan, inspect docs, or prepare a
small spec".

Recent local observation showed:

- current worktree bootstrap starts Docker Postgres, restores or fetches a
  snapshot, runs Alembic, syncs Python dependencies, and may install frontend
  dependencies
- the no-op `uv sync` cost is negligible once cached
- the expensive costs are runtime dependency preparation and frontend install
- the same full bootstrap currently runs even for docs-only or research-only
  work

That makes simple planning/documentation tasks pay the cost of runnable runtime
setup before any real implementation starts.

## Scope

This epic covers:

- the first-slice split between lightweight docs/research worktrees and full
  runnable worktrees
- the later move from slot-local Postgres containers to one repo-shared
  Postgres service with isolated per-worktree databases
- the required docs refresh and optional env ergonomics follow-up

This epic does not yet commit to:

- mandatory `direnv` usage
- changing local validation policy for docs-only PRs
- removing the existing slot model for backend/UI ports in the full bootstrap

## Target Contract

### Bootstrap modes

We want two explicit bootstrap modes.

#### Mode 1: docs

Use for:

- plans
- specs
- codebase research
- docs-only changes
- issue triage that does not need to run backend or UI processes

Contract:

- no slot required
- no Docker startup
- no Postgres snapshot restore
- no Alembic
- no Python env sync
- no UI install
- writes a minimal `.tmp_untracked/worktree.env` that marks the worktree as
  `WORKTREE_BOOTSTRAP_MODE=docs`
- keeps enough local structure that later upgrade to full bootstrap is explicit
  and simple

#### Mode 2: full

Use for:

- code changes that need runtime or validation
- backend/UI work
- tests or smoke debugging

Contract:

- explicit slot required
- writes full runtime env into `.tmp_untracked/worktree.env`
- ensures runnable dependency state
- safe to use with `scripts/worktree/run-dev.sh`

### Upgrade path

A docs-mode worktree must be upgradable in place.

Target command shape:

```bash
bash scripts/worktree/bootstrap.sh --mode full --slot 7
```

That command should overwrite the lightweight env file with the full runtime
env and prepare the worktree for dev/test commands.

### Runtime guardrails

If someone tries to run dev servers from a docs-mode worktree, the command must
fail loudly and tell them to upgrade to full bootstrap first.

## Shared Postgres Design

The current full bootstrap creates one Postgres container and volume per slot.
That is isolated, but expensive and redundant.

The target replacement is:

- one repo-managed Postgres service on a repo-managed port that is not Tal's
  own Postgres
- one template or seeded database restored once from the snapshot
- one derived per-worktree database created from that template
- one worktree-local `DATABASE_URL` that points at the isolated worktree DB

Requirements:

- no collision with Tal's own Postgres port or database names
- explicit naming and cleanup for worktree databases
- deterministic way for an agent to acquire a database for itself
- safe retirement that drops only that worktree's DB, not the whole service

## Rollout Order

1. `tal_maria_ikea-0ia.1`
   Write this plan and land the docs/research bootstrap split.
2. `tal_maria_ikea-0ia.2`
   Replace slot-local Postgres with a repo-shared Postgres service plus
   per-worktree databases.
3. `tal_maria_ikea-0ia.3`
   Refresh workflow/config docs and decide whether optional `direnv`
   integration still adds enough value.

## First Slice To Land Now

The first PR from this epic should:

- add a new lightweight command for docs/research worktrees
- extend bootstrap to support `docs` and `full` modes
- make runtime commands refuse to run from docs mode
- document when to use the lightweight path and how to upgrade

This buys immediate productivity without waiting for the shared-Postgres work.

## Open Questions

- Should docs-mode worktrees have a dedicated alias like
  `make agent-start-docs` only, or also a broader alias such as
  `make agent-start-research`?
- After the bootstrap split lands, do we also want a lighter validation command
  for docs-only changes, or is that a separate policy discussion?
- For the shared Postgres design, should per-worktree DB allocation use a
  cloned template database or a restore-on-create workflow from a single local
  snapshot artifact?
