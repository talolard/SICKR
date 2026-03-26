# AGENTS.md

Repository-wide invariants for work in `tal_maria_ikea`.

## Repository shape

- `src/ikea_agent/`: active Python runtime.
- `tests/`: pytest suite.
- `ui/`: Next.js CopilotKit UI workspace.
- `docs/`: runbooks and durable developer/user docs.
- `spec/`: product and integration specs, including `spec/ui/`.
- `plans/`: design direction and sequencing notes.
- `external_docs/`: repo-local notes for external libraries and protocols.
- `legacy/`: reference-only; do not import from it.

## Canonical instruction sources

- Repo-wide policy lives in this file.
- Role-specific behavior lives under `.codex/agents/`; see [docs/codex_multi_agent_workflow.md](docs/codex_multi_agent_workflow.md).
- Detailed workflow, transport, and UI contracts live in the linked docs/specs below rather than in `AGENTS.md`.

## Deploy Work State

- Deploy work is in post-cutover hardening, not pre-deploy architecture
  selection. One live ECS Fargate deploy has already happened, but the canonical
  release path is not yet trustworthy enough.
- The current deploy priority order is:
  - workflow reliability
  - docs accuracy
  - release provenance
  - deploy visibility later, only after the existing path is trustworthy
- The canonical target is one automatic `main -> release -> publish -> deploy`
  flow. The `manual-ref-deploy` workflow still exists in the repo, but it is
  transitional recovery debt and should be removed rather than extended.
- For deploy work, prefer the current workflows under `.github/workflows/`,
  Terraform under `infra/terraform/`, `docs/deployment_runtime_contract.md`, and
  the refreshed docs under `specs/deploy/` over older design notes.
- Older deploy plans and epics under `plans/` are historical background unless
  they are explicitly refreshed. In particular, any plan that still assumes EC2,
  SSM, host deploy bundles, or manual ECS backstops is stale and must not be
  treated as current guidance.

## Workflow invariants

- Mutating implementation work must happen in a dedicated worktree. Start new work with `make agent-start ...`; for existing assigned work, stay in the provided worktree. See [docs/worktree_multi_agent_workflow.md](docs/worktree_multi_agent_workflow.md).
- `make dev human` is reserved for Tal's canonical checkout and stable human-owned slot `90`. Agents must not use it; agents should use `make agent-start ...` in a dedicated worktree instead.
- Keep one worktree per epic or major task branch unless a human explicitly overrides that.
- Merge runs are explicit and handled from the merge queue; use `make merge-list` and follow [docs/merge_runbook.md](docs/merge_runbook.md).
- Create or update design plans in `plans/` before substantial changes.
- At task completion, update the relevant docs in `docs/` when behavior or workflow expectations changed.
- Keep changes scoped and incremental; avoid opportunistic refactors.
- Commit messages should be high-level and human-readable, with bodies that explain problem, approach, and outcome.

## Validation gates

- Python environment and commands run through `uv`.
- Required pre-commit quality gate: `make tidy`.
- `make format-all` is the quick format and lint pass without the full test suite.
- For behavioral or runtime changes, keep targeted local validation focused on the touched surface. The deferred real-UI smoke runs in CI after `PR CI` and `Dependency Review` succeed for the PR SHA; run `make ui-test-e2e-real-ui-smoke` locally only when debugging the live CopilotKit or AG-UI path.
- Probe isolation, slot-based ports, and per-worktree writable paths are documented in [docs/worktree_multi_agent_workflow.md](docs/worktree_multi_agent_workflow.md).

## Typing and test expectations

- Use explicit type annotations in production code and tests.
- Prefer small composable functions and typed dataclasses, protocols, and Pydantic models.
- Add tests for new behavior and keep them focused and fully annotated.
- Maintain 98%+ coverage on code under `src/`.
- Prefer small test files and parameterized tests where they improve clarity.

## Runtime invariants

- FastAPI plus pydantic-ai is the default runtime stack.
- Prefer chat-first UX and API surfaces over form-heavy flows.
- Keep agent state minimal and typed.
- Prefer tools that return typed domain objects over preformatted prose.
- Keep prompts concrete and explicit about expected output structure.
- Keep route handlers thin: validate input, call services or agents, return typed responses.
- Bootstrap runtime and schema at app startup; avoid hidden constructor side effects.
- Use module-level loggers via `getLogger(__name__)` and log concise operational facts.

## Implementation pointers

- Tool rendering and user-visible tool UX policy: [docs/subagent_tool_rendering_policy.md](docs/subagent_tool_rendering_policy.md)
- Deployment infrastructure source of truth: [infra/terraform/README.md](infra/terraform/README.md)
  and `specs/deploy/subspecs/20_terraform_aws_setup.md`; prefer Terraform
  outputs over ad hoc AWS discovery for deployment-owned infrastructure.
- CopilotKit and AG-UI backend protocol notes: [external_docs/pydantic_ai_ag_ui.md](external_docs/pydantic_ai_ag_ui.md)
- UI integration spec: [spec/ui/pydanticai_copilotkit_integration.md](spec/ui/pydanticai_copilotkit_integration.md)
- Frontend planning and execution guidance: [docs/frontend_delivery_guidelines.md](docs/frontend_delivery_guidelines.md)
- Frontend epic and task authoring guidance: [docs/frontend_epic_authoring.md](docs/frontend_epic_authoring.md)
- Frontend PR review and validation guidance: [docs/frontend_pr_review_guidelines.md](docs/frontend_pr_review_guidelines.md)
- Effective patterns from the March 18 floor-plan fixes:
  - prefer capability-based shared agent-shell logic over hard-coding one agent into shared flows
  - use in-flow chat primitives for page content and reserve sidebar primitives for actual sidebar UX
  - persist the rendered transcript state, not only the thread id, anywhere refresh rehydration matters
  - put user-facing labels in typed backend metadata instead of deriving them ad hoc in React
  - treat the deferred real-UI smoke path as a product contract, not only a CI wrapper detail
  - when a new eval suite is needed, copy the strongest existing repo eval architecture and change case content before changing framework shape
- Retrospective details: [docs/archive/floor_plan_agent_fixes_retrospective_2026-03-18.md](docs/archive/floor_plan_agent_fixes_retrospective_2026-03-18.md)

## Data and logging

- Keep active runtime SQL short and close to typed row-mapping code.
- Update `docs/data/` when active schema or column semantics change.
- Treat IKEA source data as static unless the task explicitly refreshes it.
- Default to native Logfire instrumentation (`instrument_pydantic_ai`, `instrument_fastapi`).
- For trace-to-code debugging, use the local `logfire-span-triage` skill.

## Project stage

- This repository is pre-production.
- For exploratory prompt and eval work, a small hand-authored dataset and an uncalibrated LLM judge are acceptable unless a task explicitly hardens them.

## Git identity

- Use the public identity for this repo:
  - `user.name = Tal Perry`
  - `user.email = talperry@users.noreply.github.com`
- Verify before pushing:
  - `git config --local --get user.name`
  - `git config --local --get user.email`
  - `./scripts/check_git_identity.sh`

## Issue tracking with Beads

- Use `bd` as the only issue tracker.
- Normal workflow:
  - `bd ready --json`
  - `bd update <id> --status in_progress --json`
  - `bd close <id> --reason "Done" --json`
- Do not create beads for pure planning, research, or tiny exploratory checks.
- Before closing an implementation issue, run `make tidy`, commit, then close it.

## Merge queue contract

- Merge queue parent: `tal_maria_ikea-0uk`.
- Merge queue items must stay `status=blocked`, assigned to `merger-agent`, and marked as merge requests (`type=merge-request` when supported, otherwise `label=merge-request`).
- Because queue items are blocked, they must not appear in normal `bd ready` pickup.
