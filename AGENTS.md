# AGENTS.md

Repository-local collaboration and implementation rules.

## Workflow

- Create/update task plans in `plans/` before substantial changes.
- At task completion, add or update relevant docs in `docs/`.
- Keep changes scoped and incremental; avoid broad refactors during setup.

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

## SQL and Data Rules

- Keep SQL in `.sql` files under `sql/`.
- Prefer DuckDB CLI + SQL scripts for schema/load/query tasks.
- Avoid embedding complex SQL inside Python unless strongly justified.
- Update `docs/data/` whenever schema or column semantics change.

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
