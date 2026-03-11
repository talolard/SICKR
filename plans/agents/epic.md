# Epic: Formalize Codex multi-agent roles, prompts, and merge-readiness workflow

## Summary

Create a project-local Codex role system that makes the multi-agent workflow explicit, repeatable, and reviewable.

This epic introduces:
- project-local role definitions for the top-level coordinator and specialized subagents
- one prompt file per role, stored next to the role config
- shared prompt-support files for reusable structure and specification guidance
- a clean split between repo-wide rules in `AGENTS.md` and role-specific behavior in role prompts
- an explicit ownership model for planning, epic decomposition, epic implementation, PR readiness, review, merge serialization, and cleanup
- updated repo guidance so merged worktrees are cleaned up and PR-readiness ownership is unambiguous

This epic is primarily about **workflow infrastructure and agent behavior**, not product/runtime features.

---

## Why we need this

The recent multi-agent run worked, but coordination was too implicit.

We saw several recurring problems:
- planning and implementation were mixed together too early
- subagent handoffs were too loose and required manual re-verification
- responsibility for PR readiness, GitHub checks, and rebasing was unclear
- merge queue handling existed, but the ownership boundary between “make it ready” and “merge it” was fuzzy
- merged worktrees were not cleaned up immediately
- some work was small enough that epic/worktree/Beads ceremony was overkill, but we did not have a clearly documented alternative path

The goal of this epic is to make those decisions explicit in code/config/prompts instead of relying on memory and repeated ad-hoc instructions.

---

## Goals

1. Define a stable set of Codex roles for this repo.
2. Give each role its own prompt file and clear behavioral contract.
3. Create shared prompt-support files for reusable epic-writing and specification guidance.
4. Keep `AGENTS.md` focused on repo-wide invariants, not agent-specific workflow details.
5. Make the top-level session explicitly behave like a coordinator/default agent.
6. Make epic ownership explicit:
   - one role thinks/specs
   - one role structures work into Beads
   - one role owns an epic to PR-ready state
   - one role serializes merges and cleans up
7. Clarify when to use the built-in `worker` role for small tasks that do not need Beads.
8. Formalize the rule that epic workers own PR readiness, including polling GitHub checks and resolving `main` drift before queueing for merge.
9. Formalize the rule that merge coordination is separate from epic implementation.
10. Add the missing cleanup expectation: merged worktrees should be removed immediately after successful merge verification.
11. Make prompt drafting itself reviewable before those prompts become active default behavior.

---

## Non-goals

This epic does **not** aim to:
- change product-facing behavior in the IKEA agent runtime
- change the Beads data model itself
- automate every aspect of GitHub or CI orchestration on day one
- fully replace human judgment about whether a task should become an epic
- introduce a separate `checks_monitor` role; for this workflow, PR checks remain owned by the epic worker

---

## Core design decisions

### 1. The starting session is the coordinator/default agent

A fresh Codex session in this repo should start as the general coordinator.

Its job is to:
- read the user request
- determine whether the user wants thinking, decomposition, a small fix, epic execution, review, or merge handling
- decide whether to remain solo or spawn a specialized role

This means the top-level role should be configured and prompted as a coordinator-oriented `default` role.

### 2. Each role gets both a TOML file and a prompt file

We will use a file layout like:

- `.codex/config.toml`
- `.codex/agents/default.toml`
- `.codex/agents/prompt.default.md`
- `.codex/agents/spec_planner.toml`
- `.codex/agents/prompt.spec_planner.md`
- `.codex/agents/epic_writer.toml`
- `.codex/agents/prompt.epic_writer.md`
- `.codex/agents/epic_worker.toml`
- `.codex/agents/prompt.epic_worker.md`
- `.codex/agents/worker.toml`
- `.codex/agents/prompt.worker.md`
- `.codex/agents/repo_explorer.toml`
- `.codex/agents/prompt.repo_explorer.md`
- `.codex/agents/docs_researcher.toml`
- `.codex/agents/prompt.docs_researcher.md`
- `.codex/agents/pr_reviewer.toml`
- `.codex/agents/prompt.pr_reviewer.md`
- `.codex/agents/merge_coordinator.toml`
- `.codex/agents/prompt.merge_coordinator.md`

Rule:
- each role TOML contains the role metadata/config
- each role prompt file contains the role’s behavioral instructions
- each role’s custom instructions should explicitly tell it to read its own prompt file

### 3. Prompt-file convention should be strict and obvious

To avoid ambiguity, each role should have a single obvious prompt file path.

Example:
- role config: `.codex/agents/epic_worker.toml`
- role prompt: `.codex/agents/prompt.epic_worker.md`

The TOML/config should reference the prompt path explicitly, or the role instructions should explicitly say to load that exact file before acting.

### 4. Shared prompt-support files should hold reusable structure and process guidance

Not every useful instruction belongs directly inside one role prompt.
Some guidance is reusable across multiple roles and should live in shared prompt-support files.

In particular we should introduce:
- `.codex/prompt_support/epic_structure.md`
- `.codex/prompt_support/spec_planner_guide.md`
- `.codex/prompt_support/openai_plan_mode.md`

How they should be used:
- `epic_writer` should read and apply `epic_structure.md` when decomposing approved work.
- `spec_planner` should read and apply `spec_planner_guide.md` and `openai_plan_mode.md` when helping the user iterate on a specification.
- `epic_worker` should also read `epic_structure.md` so it understands what a strong epic/task breakdown looks like and can sanity-check whether the implementation work graph is adequate.

Why:
- It avoids duplicating the same structural guidance across multiple prompts.
- It keeps prompts focused on role mission and behavior, while shared files hold reusable process patterns.
- It lets us improve the reusable structure once and benefit across multiple roles.

### 5. `AGENTS.md` remains the repo-wide source of truth for invariants

`AGENTS.md` should continue to own instructions that are true regardless of role, including:
- repo structure
- workflow invariants that apply to all mutating work
- validation gates
- typing/test standards
- tool rendering contracts
- runtime/data/logging policies
- Git identity rules
- Beads as the sole issue tracker

Role prompts should own instructions that are only relevant to a specific kind of agent behavior.

---

## Proposed roles

### `default`

Role:
- top-level coordinator for the session

Responsibilities:
- classify the incoming request
- choose whether to spawn `spec_planner`, `epic_writer`, `worker`, `epic_worker`, `repo_explorer`, `docs_researcher`, `pr_reviewer`, or `merge_coordinator`
- remain the user-facing orchestrator throughout the session

Why:
- keeps the user talking to one stable top-level session
- centralizes routing decisions

### `spec_planner`

Role:
- help the human think through scope, approach, risks, and tradeoffs

Responsibilities:
- clarify goals and open questions
- separate what is known from what is still speculative
- shape a good approach before work is decomposed into Beads
- explicitly ask whether we have what we need, whether the goal is clear, and whether the key decisions are known
- use the shared guidance in `.codex/prompt_support/spec_planner_guide.md` and `.codex/prompt_support/openai_plan_mode.md`

Why:
- separates planning/spec thinking from task breakdown and implementation

### `epic_writer`

Role:
- turn approved requirements and plan notes into tracked work

Responsibilities:
- create goals, epics, tasks, dependencies, acceptance criteria, references
- create the merge-request task and GitHub-check gateway structure
- ensure the work graph matches the intended implementation/merge workflow
- apply the structural guidance in `.codex/prompt_support/epic_structure.md`

Why:
- separates decomposition from implementation

### `epic_worker`

Role:
- own one epic in one dedicated worktree until it is PR-ready

Responsibilities:
- implement the epic
- run focused tests, then repo-required validation
- open/update the PR
- poll GitHub checks periodically
- fix failing checks
- refresh with `main` and resolve conflicts before calling the branch ready
- understand the intended work graph and acceptance criteria by reading `.codex/prompt_support/epic_structure.md`
- hand back: worktree, branch, commit, PR, validations, blockers

Why:
- creates one accountable owner for PR readiness

### `worker`

Role:
- handle small, narrow implementation tasks that do not deserve epic/Beads overhead

Responsibilities:
- make the smallest defensible change
- keep scope tight
- run focused validation

Why:
- avoids over-processing simple tasks

### `repo_explorer`

Role:
- read-only codebase navigation and ownership discovery

Responsibilities:
- trace code paths
- identify owning files and entry points
- answer “where should this change live?” without editing

Why:
- reduces mutation-time confusion

### `docs_researcher`

Role:
- read-only external docs / API behavior verification

Responsibilities:
- use official docs / MCP-backed sources
- answer framework/API questions succinctly

Why:
- reduces drift and assumption errors

### `pr_reviewer`

Role:
- independent correctness/review pass on a ready branch or PR

Responsibilities:
- inspect diffs and validation coverage
- identify correctness, regression, or readiness gaps
- return actionable findings only

Why:
- introduces a review layer between “implemented” and “queued to merge”

### `merge_coordinator`

Role:
- serialized merge-run owner

Responsibilities:
- process merge-request tasks from the merge queue only
- verify mergeability
- if needed, perform the final refresh with `main`, rerun required validation, and land the PR
- close merge-request Beads
- remove merged worktrees immediately

Why:
- keeps merge ordering disciplined and cleanup predictable

---

## Ownership model

### Epic worker owns PR readiness

For epic-sized work, the epic worker is responsible for getting the branch to a state where it is genuinely ready to merge.

That includes:
- local validation
- PR creation/update
- GitHub checks polling
- fixing red checks
- resolving branch drift with `main`
- rerunning required validation after conflict resolution

### Merge coordinator owns serialized landing

The merge coordinator should not be the agent that initially implements the epic.

It owns:
- queue discipline
- one-by-one merge execution
- final merge-time verification
- merge bead closure
- post-merge worktree cleanup

This split resolves an important ambiguity:
- the epic worker makes the branch ready
- the merge coordinator lands it in order

---

## Epic / Beads structure we should adopt

For epic-sized work, the Beads graph should look like:

- Goal (optional, for multi-epic bodies of work)
  - Epic
    - implementation task A
    - implementation task B
    - implementation task C
    - gateway: GitHub checks green
    - merge-request task

Dependencies:
- the merge-request task depends on all implementation tasks
- the merge-request task depends on the GitHub-checks-green gateway
- the epic is not complete until the merge-request task is closed by successful merge

This creates a clean distinction between:
- “the code exists”
- “the PR is green and mergeable”
- “the work is actually merged”

---

## What stays in `AGENTS.md` vs what moves to prompts

## Keep in `AGENTS.md` (repo-wide invariants)

These apply across roles and should stay global:
- repository structure
- external docs lookup policy
- create/update plans in `plans/` before substantial changes
- update docs at task completion
- use dedicated worktrees for mutating work
- merge runs are explicit and use the merge runbook
- one worktree per epic / avoid mutating `main`
- merge queue parent and queue shape expectations
- `make tidy` requirement
- behavioral readiness gate (`make ui-test-e2e-real-ui-smoke`)
- typing/test standards
- runtime/tool rendering/data/logging rules
- Git identity source of truth
- Beads as the sole tracker

## Move to `prompt.default.md`

These are coordinator behaviors, not repo invariants:
- how to classify user requests into thinking / decomposition / small fix / epic / review / merge
- when to spawn specialized roles
- how to stay user-facing while orchestrating subagents
- how to decide between `worker` and `epic_worker`

## Move to `prompt.spec_planner.md`

- think-first behavior
- clarify goals, tradeoffs, and risks
- encourage iterative questioning and reflective summaries
- explicitly ask meta-questions like “do we have what we need?”, “do we know the goal?”, and “do we know the key decisions?”
- read `.codex/prompt_support/spec_planner_guide.md`
- read `.codex/prompt_support/openai_plan_mode.md`
- no code edits

## Move to `prompt.epic_writer.md`

- create goals/epics/tasks from approved requirements
- write explicit dependencies, acceptance criteria, references
- always model merge-request task + GitHub-check gateway
- read `.codex/prompt_support/epic_structure.md`
- do not implement code

## Move to `prompt.epic_worker.md`

- work only in the assigned worktree
- own the specified epic/tasks/files
- read `.codex/prompt_support/epic_structure.md` so the worker understands what a good epic/task graph should look like
- open/update the PR
- poll GitHub checks
- fix failing checks
- refresh with `main` before declaring readiness
- provide standardized handoff format

## Move to `prompt.worker.md`

- use for small tasks only
- do not create epic-grade ceremony when not needed
- keep changes minimal and tightly scoped

## Move to `prompt.repo_explorer.md`

- stay read-only
- map code paths, symbols, and ownership
- return evidence rather than speculative rewrites

## Move to `prompt.docs_researcher.md`

- use primary sources
- stay read-only
- answer API/framework questions only

## Move to `prompt.pr_reviewer.md`

- stay read-only
- inspect diffs/validation for correctness and readiness
- return concrete findings only

## Move to `prompt.merge_coordinator.md`

- process merge queue only
- assume epic worker owns readiness but verify mergeability
- resolve final queue-time conflicts if required
- close queue beads and clean merged worktrees immediately
- keep merge serialization strict

---

## Conflicts and resolutions

### Conflict 1: `AGENTS.md` vs prompt files could duplicate instructions

Problem:
- if both files repeat the same rules, drift is inevitable

Resolution:
- `AGENTS.md` owns repo-wide invariants
- prompts own role-specific behavior
- prompts may reference `AGENTS.md`, but should not restate large global policy blocks unless necessary

### Conflict 2: built-in roles vs custom role prompts

Problem:
- built-in roles like `default` and `worker` already exist
- we still want repo-specific prompt files for them

Resolution:
- use project-local role definitions/config to wrap or override built-ins where needed
- preserve the semantic meaning of the built-in role name, but add repo-specific prompt loading and instructions

### Conflict 3: who owns check polling?

Problem:
- a separate `checks_monitor` could split accountability

Resolution:
- do **not** create a separate checks-monitor role for this workflow
- `epic_worker` owns PR checks and readiness end-to-end
- if we later discover polling is too distracting, we can revisit, but the default should be single-accountability

### Conflict 4: who owns merge-time conflict resolution?

Problem:
- the epic worker should keep the branch current, but `main` can still move after queueing

Resolution:
- epic worker owns pre-queue conflict resolution and readiness
- merge coordinator owns final queue-time refresh/merge handling if `main` moved after queueing
- after any final merge-time conflict resolution, required validation must rerun

### Conflict 5: small tasks vs epic tasks

Problem:
- if we route everything through Beads + worktrees, we create unnecessary ceremony

Resolution:
- explicitly document that built-in `worker` is preferred for small, well-understood tasks that do not need Beads
- reserve `epic_worker` for work that truly merits dedicated worktree + PR-readiness ownership

### Conflict 6: role prompts might become the new dumping ground

Problem:
- moving agent-specific instructions out of `AGENTS.md` could simply relocate bloat

Resolution:
- each prompt should explain only:
  - the role’s mission
  - what it owns
  - what it must not do
  - what output/handoff it must return
- keep prompts narrow and task-specific

### Conflict 7: shared prompt-support files could hide too much behavior

Problem:
- if too much logic moves into shared support files, the role prompt itself may become unclear
- reviewers may have to chase too many files to understand one role

Resolution:
- role prompts should remain readable on their own
- shared support files should contain reusable structure/process guidance, not replace the role mission
- each role prompt should explicitly list which support files it reads and why

### Conflict 8: Git identity drift between AGENTS and scripts

Problem:
- the source-of-truth identity and the checker can diverge

Resolution:
- update `AGENTS.md` and `./scripts/check_git_identity.sh` together
- treat them as one contract

---

## Proposed deliverables

### Shared prompt-support files

- `.codex/prompt_support/epic_structure.md`
- `.codex/prompt_support/spec_planner_guide.md`
- `.codex/prompt_support/openai_plan_mode.md`

### Config and role files

- `.codex/config.toml`
- `.codex/agents/default.toml`
- `.codex/agents/spec_planner.toml`
- `.codex/agents/epic_writer.toml`
- `.codex/agents/epic_worker.toml`
- `.codex/agents/worker.toml`
- `.codex/agents/repo_explorer.toml`
- `.codex/agents/docs_researcher.toml`
- `.codex/agents/pr_reviewer.toml`
- `.codex/agents/merge_coordinator.toml`

### Prompt files for review

- `.codex/agents/prompt.default.md`
- `.codex/agents/prompt.spec_planner.md`
- `.codex/agents/prompt.epic_writer.md`
- `.codex/agents/prompt.epic_worker.md`
- `.codex/agents/prompt.worker.md`
- `.codex/agents/prompt.repo_explorer.md`
- `.codex/agents/prompt.docs_researcher.md`
- `.codex/agents/prompt.pr_reviewer.md`
- `.codex/agents/prompt.merge_coordinator.md`

### Repo guidance updates

- `AGENTS.md` adjustments to remove role-specific sections and clarify new ownership boundaries
- possible runbook updates in `docs/` if we want a user/developer-facing explanation of the role workflow
- script alignment for git identity checker

---

## Sequencing / task breakdown

### Phase 1: role design and prompt drafting

1. Create `.codex/config.toml` scaffold.
2. Create role TOML files.
3. Create shared prompt-support files.
4. Draft prompt files for each role.
5. Present prompt files for human review before enabling them broadly.

### Phase 2: instruction partitioning

6. Audit `AGENTS.md` and mark each section as:
   - repo-wide invariant
   - default/coordinator behavior
   - role-specific behavior
7. Move role-specific instructions into prompt files.
8. Move reusable structure/process guidance into shared prompt-support files.
9. Trim `AGENTS.md` so it is cleaner and more global.

### Phase 3: workflow formalization

10. Update `AGENTS.md` to clarify:
   - epic worker owns PR readiness and GitHub checks
   - merge coordinator owns serialized landing and cleanup
   - built-in `worker` is for small tasks without Beads
   - merged worktrees must be cleaned up immediately after merge
11. Document Beads merge-gate structure for epics.
12. Align `scripts/check_git_identity.sh` with the repo source of truth.
13. Dry-run the role workflow in one contained epic and adjust prompts/config based on what actually worked.

---

## Acceptance criteria

This epic is done when:
- the repo has explicit project-local Codex role config
- each role has a reviewable prompt file next to its TOML config
- reusable prompt-support files exist for epic structure and spec-planning guidance
- `AGENTS.md` contains only repo-wide invariants plus minimal workflow rules that apply globally
- role-specific behavior has moved to role prompts
- the startup/default role clearly knows how to route work to the right specialized role
- epic worker vs merge coordinator ownership is explicit and documented
- built-in `worker` usage for small tasks is explicitly documented
- merged-worktree cleanup is explicitly part of the merge workflow
- git identity instructions and checker agree
- prompt files have been reviewed by the human before broad adoption

---

## Review gate requested by Tal

Before these role prompts are treated as live/default behavior, the prompt files themselves should be reviewed.

That means this epic should explicitly include a human review checkpoint after prompt drafting and before rollout.

The initial implementation of this epic should therefore prioritize:
- drafting role files
- drafting prompt files
- presenting them for review
- only then wiring them fully into the working default flow

