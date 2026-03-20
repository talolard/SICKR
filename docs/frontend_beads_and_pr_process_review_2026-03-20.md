# Frontend Beads and PR Process Review

Date: 2026-03-20

## Purpose

Review the recent frontend work definitions and delivery flow around the March 19 to March 20 UI effort, compare the Beads definitions to what actually shipped in PRs `#70`, `#71`, and `#72`, and define better standards for:

- Beads epic and task definitions
- handoffs and validation expectations
- PR descriptions and review process

## Artifacts reviewed

- Beads epics and tasks:
  - `tal_maria_ikea-mi4`
  - `tal_maria_ikea-mi5`
  - `tal_maria_ikea-mi6`
  - `tal_maria_ikea-7oz`
  - `tal_maria_ikea-19u`
- PRs:
  - `#70` `MI4: polish March 19 UI interactions and layout`
  - `#71` `MI5 planning: map Stitch editorial redesign onto the current UI`
  - `#72` `Close Stitch rollout gaps in the agent workspaces`
- Supporting docs:
  - `spec/uxui-march19/feedback.md`
  - `spec/uxui-march19/designer_review_brief.md`
  - `spec/uxui-march19/report.md`
  - `plans/stitch_editorial_redesign_mapping_2026-03-19.md`
  - `docs/frontend_delivery_guidelines.md`

## Executive summary

The short version:

- `MI4` was defined well and `PR #70` largely matched it.
- `MI5` was also defined reasonably well, but `PR #71` only shipped the home/theme slice while the UI began to look more complete than it really was.
- `MI6` and `7oz` captured review comments well, but the review loop stayed focused on the home slice and did not force a route-family parity check.
- `19u` correctly identified the missing rollout work, but it duplicated work already present in open `MI5` tasks and its status was not kept in sync with implementation.

The main failure was not that Beads was too vague everywhere. The main failure was that the process allowed:

- route-family work to be communicated as if it were broader than the routes actually touched
- implementation tasks to be closed before merge-ready validation was truly complete
- overlapping epics to exist for the same remaining frontend slice
- PR review to focus on touched surfaces without requiring an explicit statement about untouched sibling surfaces

## Comparison of work definitions to delivered work

| Work packet | What the Beads definition said | What the PR actually delivered | Assessment |
| --- | --- | --- | --- |
| `tal_maria_ikea-mi4` -> `#70` | Tight scope, clear file families, explicit verifiable outcomes around thread stability, bounded chat, result readability, launcher polish, and real-page coverage | `#70` delivered those exact outcomes and described them well in the PR body | Strong definition quality. The main issue was status timing: the epic and tasks were closed hours before the PR fully stabilized and merged |
| `tal_maria_ikea-mi5.1` to `.3` -> `#71` | Planning import, theme/chrome foundation, and home/launcher redesign | `#71` delivered those three tasks and documented them clearly | Good task clarity. The problem was not the task graph itself |
| `tal_maria_ikea-mi5` epic overall after `#71` | Epic definition of done included agent-page shell adoption, search/floor-plan parity, and updated regression coverage | `#71` merged without those route-family outcomes; only the home/theme slice was complete | Acceptable epic definition, weak route-slice communication. The epic stayed open, which was correct, but the merge still created an app-level visual mismatch |
| `tal_maria_ikea-mi6` and `tal_maria_ikea-7oz` inside `#71` | Precise review-fix epics for theme fidelity, home composition, and CI-equivalent verification | The review-fix commits improved home fidelity and validation reporting, but did not address untouched agent routes | Good local review-fix task quality, but the process let review energy stay too local to the touched slice |
| `tal_maria_ikea-19u` -> `#72` | Explicit route-level corrective work for shared shell, consultation rail, floor-plan, image-analysis, home cleanup, and route-level verification | `#72` implements that corrective slice well and adds workflow guidance | Good corrective definition, but too much overlap with still-open `MI5.4` to `MI5.8` |

## What was clear enough

These parts worked well and should be preserved:

- User-visible goals were usually named directly instead of hiding behind implementation language.
- Most tasks listed concrete file families or seams.
- Verifiable outcomes were written in observable product language.
- Dependencies were generally sensible.
- The later corrective epic `19u` was especially strong at naming the missing routes and the missing shared-shell contract.
- PR `#70` is a good example of a PR body that explains problem, approach, outcome, and validation in reviewer-usable language.

## What was not clear enough

### 1. Route coverage was not mandatory enough

This was the biggest frontend process gap.

`MI5` knew the redesign was broader than home, but neither the Beads workflow nor the PR review process required an explicit route matrix in every artifact. That let a home-first slice feel visually larger than it really was.

Consequence:

- `#71` was technically honest in parts of its body, but the branch still landed in a state where home looked editorial while the live workspaces remained on the older shell.

### 2. Epic closure discipline was too loose

`MI4` tasks were closed before the full PR lifecycle finished. Later commits in `#70` still had to stabilize mock flows and restore coverage.

Consequence:

- Beads no longer represented the actual implementation state during the most important review and CI phase.

### 3. Overlapping frontend epics created duplicate truth

`MI5.4` to `MI5.8` already described the shared shell, search, floor-plan, consultation rail, and redesign validation work. `19u` then restated much of the same remaining work in a second epic.

Consequence:

- handoff clarity got worse, not better
- it became ambiguous which task set should be closed when the implementation landed
- reviewers and future agents had two partially valid maps of the same remaining work

### 4. Review-fix work did not force a whole-route-family check

`MI6` and `7oz` were good review-fix epics, but they were structured around home-fidelity comments and CI checks. Nothing in that process required asking: "does the untouched route family now look inconsistent enough that this merge should be gated on follow-up work?"

Consequence:

- the review loop improved the local slice while the cross-route mismatch became more visible

### 5. Validation definitions were still too command-centric

The recent work did run strong validation, but the task definitions and PR bodies still leaned more on command lists than on a manual route/state verification matrix.

Consequence:

- important human checks were performed, but they were not always encoded as required acceptance criteria

### 6. Branch hygiene after squash merges needs a rule

`#72` is a correct follow-up PR in diff terms, but its commit list includes older commits from the already-squashed `#71` branch history because the follow-up branch was cut from the prior branch head instead of from `main`.

Consequence:

- the GitHub commit list is noisier than necessary
- reviewers have to reason harder about what is actually new

## Standards for defining frontend work in Beads

### Standard 1: Every frontend epic must include a route matrix

Required fields:

- routes in scope
- routes explicitly deferred
- shared surfaces affected
- design references used for each route family

Why:

- This prevents a home-only or shell-only slice from being mistaken for app-wide parity.

### Standard 2: Every frontend task must include a state matrix

Required states:

- empty
- loading
- success
- long-content or stress
- error or fallback

Why:

- Most frontend regressions in this repo came from state handling, not static styling.

### Standard 3: Every task must include explicit non-goals

Required section:

- what this task will not change
- what runtime seams must remain intact

Examples:

- no backend architecture changes
- preserve CopilotKit runtime shape
- preserve Three.js floor-plan rendering path

Why:

- This makes review and handoff faster and prevents accidental architecture churn.

### Standard 4: Frontend tasks should be one of four types

Allowed task shapes:

- shared contract or shell task
- route slice task
- validation task
- review-fix task

Why:

- These types have different acceptance criteria and should not be mixed casually inside one task.

### Standard 5: Frontend tasks must define validation in user-visible language first

Required structure:

- manual acceptance checks
- automated checks
- known stress cases

Why:

- A shell command is not itself the acceptance criterion.

### Standard 6: Do not duplicate open tasks across epics without an explicit supersession rule

If a retrospective changes the framing of existing open work:

- update the original open tasks, or
- create replacement tasks that explicitly say they supersede the earlier ones

Why:

- Multiple active task graphs for the same route family are a handoff hazard.

### Standard 7: Do not close implementation tasks until merge readiness is real

Minimum closure bar for frontend implementation tasks:

- required validation has passed on the final branch state
- PR description is current
- the task notes include the PR number and final validation summary
- if the repo expects merge-based completion, the task is at least merge-ready

Why:

- Closing tasks before the late CI and review phase makes Beads stop representing reality.

### Standard 8: Handoff notes must be mandatory on open frontend tasks

Required handoff note fields:

- what is already shipped on the branch
- what still blocks merge
- what was visually checked
- what remains visually unchecked
- what specific risk to verify next

Why:

- Frontend work often spans multiple review loops, and visual state is easy to lose across agent context changes.

## Recommended frontend Beads template

Each frontend epic should contain:

- Goal
- Routes in scope
- Routes deferred
- Shared contracts affected
- Design references
- Definition of done
- Validation matrix

Each frontend task should contain:

- Goal
- Scope
- Non-goals
- Dependencies
- Manual acceptance
- Automated acceptance
- Verifiable outcome
- Handoff note placeholder

## Standards for PR descriptions

Every frontend PR should include these sections:

- Summary
- Routes covered
- Routes deferred
- Shared contracts affected
- Design references checked
- Beads tasks closed in this PR
- Beads tasks intentionally left open
- Validation
- Remaining risks

Why:

- This makes it much easier to review whether the PR is honest about scope.

### Additional PR rules

- If the PR only covers one slice of a broader epic, say that in the first paragraph.
- If the PR is a review-fix pass, state whether route coverage changed or not.
- If the PR follows a squash merge, cut the follow-up branch from `main` or cherry-pick the new commits so the commit list stays reviewable.
- For visual work, include named reference artifacts, not only general design claims.
- If the PR changes chat or tool-rendering UI, mention the long-content and raw-payload stress behavior explicitly.

## PR review checklist for frontend work

Reviewers should explicitly answer:

1. Which routes are actually covered by this PR?
2. Which sibling routes remain intentionally old or incomplete?
3. Does the PR touch a shared shell or only a local slice?
4. If it touches only a local slice, does the PR description avoid app-wide claims?
5. Were the touched routes compared against named design references?
6. Were fresh-thread, existing-thread, success, and long-content states checked?
7. If CopilotKit or transcript styling changed, were scroll ownership and long raw payload behavior checked?
8. Are the Beads tasks and PR body synchronized about what is done versus deferred?
9. If the branch follows a squash-merged predecessor, is the commit history still reviewer-friendly?

## Recommended validation process for frontend merges

1. Validate the shared contract first.
2. Validate each touched route against the route matrix.
3. Run the required automated checks.
4. Update the PR body with what was actually verified.
5. Only then close the Beads tasks tied to the shipped slice.

For route-family work, the manual check should always include:

- one canonical desktop viewport
- one fresh thread
- one existing thread
- one realistic success path
- one long-content or raw-tool-output stress case

## Recommended process changes for this repo

Short-term:

- add a frontend Beads molecule or template with the required route/state/non-goal fields
- add a frontend PR template section for route coverage and deferred routes
- require Beads task notes to record final validation and PR number before closure

Medium-term:

- decide whether `19u` supersedes `MI5.4` to `MI5.8` or whether those original `MI5` tasks should remain the canonical execution tasks
- avoid creating a second epic for the same remaining route-family work unless the supersession story is explicit
- add a review habit that asks for a route matrix before approving any design-heavy frontend PR

## Bottom line

The Beads work itself was often better than the delivery process around it. The main process improvements needed are:

- force route coverage clarity earlier
- make deferred work impossible to hide
- keep one canonical task graph for a frontend slice
- close tasks only when merge readiness is real
- make PR review explicitly responsible for route-family honesty, not just local fidelity
