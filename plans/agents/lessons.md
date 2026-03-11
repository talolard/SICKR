# Lessons from the multi-agent epic workflow

## Outcome

The workflow was successful: we split work by epic, used dedicated worktrees, validated branches, opened PRs, merged them one at a time, and then cleaned merged worktrees. The main remaining lesson is not whether the workflow works, but how to make it more repeatable and less coordinator-heavy.

## What worked well

- Splitting work by epic reduced interference and made branch ownership clearer.
- Dedicated worktrees were a strong fit for parallel implementation.
- Beads worked well for persistent task tracking, merge queue management, and post-merge closure.
- Strong validation gates (`make tidy` and the real UI smoke) caught issues before merge.
- A single serialized merge flow reduced landing risk.

## Main frictions we hit

### 1. Planning and execution were mixed too early

We started by thinking and implementing in the same loop. That made it harder to tell when work was actually well-scoped versus still being designed.

### 2. Subagent handoffs were too loose

Subagents were most useful as parallel implementers, but their summaries were not reliable enough to accept without review. We still had to inspect diffs, validation output, and branch state directly.

### 3. PR readiness ownership was fuzzy

There was uncertainty around who should:
- watch GitHub checks
- fix red builds
- resolve drift with `main`
- decide when a PR is genuinely ready for merge

### 4. Merge execution and cleanup were not fully systematized

The merge queue itself worked, but post-merge cleanup—especially worktree cleanup—was not automatic enough.

### 5. Not every task needed epic-grade process

Some work is truly epic-sized and benefits from Beads, worktrees, PR-readiness loops, and merge-queue discipline. Some work is just a small fix. We need an explicit distinction so we do not over-process simple tasks.

## Proposed role model

The official Codex multi-agent guidance recommends narrow, opinionated roles with one clear job, plus role-specific config layered through `.codex/config.toml` and per-role config files. Codex also ships built-in roles including `default`, `worker`, `explorer`, and `monitor`, and shows examples of custom roles such as `reviewer` and `docs_researcher`.

### `spec_planner`

Use when the human wants help thinking.

Responsibilities:
- clarify goals
- surface tradeoffs and architecture boundaries
- identify risks and unknowns
- shape a good implementation approach before work decomposition

Why:
- solves the “planning mixed with doing” problem

### `epic_writer`

Use when requirements are understood well enough to turn into tracked work.

Responsibilities:
- convert requirements and approved plan notes into Beads goals, epics, and tasks
- define dependencies and acceptance criteria
- create merge-readiness structure, including merge-request task and GitHub-check gate

Why:
- separates work decomposition from implementation
- makes the task graph explicit before code starts

### `epic_worker`

Use for one epic in one dedicated worktree.

Responsibilities:
- implement the epic
- validate locally
- open/update the PR
- poll GitHub checks until green
- fix failing checks
- refresh with `main` and resolve conflicts before declaring readiness
- hand back: worktree, branch, commit, PR, validations, blockers

Why:
- gives one agent end-to-end ownership of PR readiness
- solves the “who owns checks and rebases?” problem

### `worker` (built-in default)

Use for small, narrow implementation tasks that do not justify Beads overhead.

Responsibilities:
- implement a small fix
- keep the change tightly scoped
- run focused validation

Why:
- avoids over-processing simple work
- fits the built-in Codex `worker` role, which is explicitly execution-focused for implementation and fixes

### `repo_explorer`

Use when we need codebase mapping without editing.

Responsibilities:
- trace real code paths
- identify owning files and entry points
- return evidence, not broad rewrite suggestions

Why:
- reduces mutation-time confusion
- gives workers a precise map before edits

### `docs_researcher`

Use when external APIs or framework behavior need confirmation.

Responsibilities:
- check official docs and MCP-backed references
- return concise source-backed answers
- avoid code changes

Why:
- prevents framework/API drift from leaking into implementation guesses

### `pr_reviewer`

Use after a branch is believed to be ready.

Responsibilities:
- review diffs like an owner
- focus on correctness, regressions, missing validation, and merge risk
- provide concrete findings only

Why:
- adds a quality check between “implemented” and “queued for merge”

### `merge_coordinator`

Use only for serialized merge handling.

Responsibilities:
- process merge-request tasks from the merge queue
- verify mergeability
- handle final refresh with `main` if needed
- rerun required validation after conflict resolution
- merge one PR at a time
- close merge-request tasks
- remove merged worktrees immediately

Why:
- keeps merge ordering disciplined
- keeps cleanup predictable
- prevents the coordinator from having to do all implementation work too

## Recommended process

### Phase 1: think
- Use `spec_planner` to shape the approach.

### Phase 2: structure
- Use `epic_writer` to create the Beads graph.
- Each epic should include:
  - implementation tasks
  - a GitHub-checks-green gateway
  - a merge-request task

### Phase 3: implement
- Give one `epic_worker` one epic and one worktree.
- The epic worker owns PR readiness, including GitHub check polling and keeping the branch current with `main`.

### Phase 4: review
- Use `repo_explorer`, `docs_researcher`, or `pr_reviewer` as support roles when needed.

### Phase 5: merge
- Queue the merge-request task once the epic worker has the branch green and conflict-free.
- Let the `merge_coordinator` perform the final serialized merge and cleanup.

## Action items

### 1. Update AGENTS.md
Add or clarify:
- merged worktrees must be removed immediately after merge verification
- epic worker owns PR readiness and GitHub-check polling
- merge coordinator owns final serialized merge and cleanup
- built-in `worker` is preferred for small tasks that do not need Beads
- subagent handoff format should be standardized

### 2. Align git identity tooling
- Keep `AGENTS.md` and `./scripts/check_git_identity.sh` in sync so the checker matches the stated source of truth.

### 3. Formalize role config
Create project-local Codex role config for:
- `spec_planner`
- `epic_writer`
- `epic_worker`
- `repo_explorer`
- `docs_researcher`
- `pr_reviewer`
- `merge_coordinator`

### 4. Formalize the epic merge gate
For epic-sized work, model:
- implementation tasks
- GitHub checks gateway
- merge-request task blocked by both

### 5. Standardize subagent handoff
Require every implementation handoff to include:
- worktree
- branch
- commit
- PR
- validations run
- blockers only

## Practical takeaway

The best pattern for us is not “many autonomous agents each doing everything.” It is:
- one role for thinking
- one role for structuring work
- one role for owning an epic to PR-ready
- light support roles for exploration, docs, and review
- one role for serialized merge and cleanup

That keeps parallelism where it helps and coordination where it matters.
