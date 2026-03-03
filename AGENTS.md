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
- Use `make format-all` as the go-to local quality command (no tests).
- Run `make tidy` before commit.
- Quality gate for changes:
  - `make format-all`
  - `make test`

## Typing and Test Expectations

- Use explicit type annotations in production code and tests.
- Prefer small composable functions and typed dataclasses/protocols.
- Add tests for new behavior; Test extensively.
- Use codecov and maintain 98%+ coverage on all code in `src/`.
- Keep test files small, prefer paramaterized tests. Make sure tests are fully type annotated.
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
- When analysing data yourself, view small result sets and aggregates first, to avoid consuming a lot of data at once.
- Maintain a docs/data_patterns.md with patterns you notice in the data, and queries that work or dont. reference it often and keep it updated.

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

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking except the exceptions described below
Plans and specs give our direction, define the work in beads.

Each task in beads that you add should

- Have a title of what the task is "Save vectors in parquet format" not "Use parquet"
- Have a context section "Currently we recompute vectors in dev, easier to store in parquet so duckdb can just load them quickly"
- Have a definition of done section "All embeddings are stored in parquet, paritioned, test checks we can load them and create an index + queries still work"
- Reference plan spec and additional md files , as well as the docs and external docs.

### When not to use bd / beads

- When the user asks you to plan or research, don't put planning and research in beads just do it.
- When the user asks for small exploratory work or a check "which file is this function in?" "what does this error mean?" "what are the current embedding strategies we have?" do the work and report back without creating beads for it. If you find something that needs follow up work, then create a bead for the follow up work but not for the initial exploration.
-

### Closing a task

- Befoore closing, lint, type check, test, ensure coverage. Write a descriptive commit message and commit. Once all those happened, close the task.
-
-

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists aside from what the user tells you to.
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->
