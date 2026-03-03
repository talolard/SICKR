# AGENTS.md

Repository-local collaboration and implementation rules.

## Workflow

- Create/update task plans in `plans/` before substantial changes.
- At task completion, add or update relevant docs in `docs/`.
- Keep changes scoped and incremental; avoid broad refactors during setup.
- Commit at the end of each implementation subtask.
- Commit messages must be high-level and human-readable, focused on intent.
- Commit bodies should explain problem -> approach -> outcome, not just file lists.

## Tooling Standards

- Python environment and commands run through UV.
- Run `make tidy` before commit.
- Quality gate for changes:
  - `make lint`
  - `make format-check`
  - `make typecheck`
  - `make test`

## Typing and Test Expectations

- Use explicit type annotations in production code and tests.
- Prefer small composable functions and typed dataclasses/protocols.
- Add tests for new behavior; keep smoke tests passing at minimum.
- Keep files short and split modules before they become hard to scan.

## Django Standards

- Use only class-based views (CBVs); do not add function-based views.
- Keep Django files focused and short (views/forms/services split by responsibility).
- Prefer reusable template snippets (`include`/partials) over large monolithic templates.
- Keep web layer thin: call retrieval/service interfaces rather than embedding heavy logic in views.

## SQL and Data Rules

- Keep SQL in `.sql` files under `sql/`.
- Prefer DuckDB CLI + SQL scripts for schema/load/query tasks.
- Avoid embedding complex SQL inside Python unless strongly justified.
- Update `docs/data/` whenever schema or column semantics change.
- Treat the IKEA source dataset as static for this project unless we explicitly decide to refresh it.

## Logging

- Use shared logger configuration from `src/tal_maria_ikea/logging_config.py`.
- Include query/request IDs in pipeline logs where available.

## Git Identity

- This repo must use the public identity:
  - `user.name = Talo Lard`
  - `user.email = talolard@users.noreply.github.com`
- Verify before pushing:
  - `git config --local --get user.name`
  - `git config --local --get user.email`
  - `./scripts/check_git_identity.sh`
