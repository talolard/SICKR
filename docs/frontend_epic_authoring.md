# Frontend Epic Authoring

Operational guidance for defining frontend work in Beads.

Use this when creating or revising frontend epics and child tasks. The goal is to make route coverage, design references, preserved runtime seams, and validation expectations explicit before code changes start.

## What every frontend epic must contain

- Goal:
  - the user-visible outcome, not only implementation language
- Routes in scope:
  - exact routes and surfaces being changed
- Routes deferred:
  - exact sibling routes intentionally not being changed
- Shared contracts affected:
  - shared shells, rails, renderers, layout rules, or interaction contracts
- Design references:
  - exact screenshots, exported HTML, or design docs used for comparison
- Definition of done:
  - route-family and validation outcomes in observable product language
- Validation matrix:
  - manual states plus automated checks
- Non-goals:
  - what must remain intact and what is deliberately out of scope

## What every frontend task must contain

- Goal
- Scope
- Non-goals
- Dependencies
- Manual acceptance
- Automated acceptance
- Verifiable outcome
- Handoff notes while the task remains open

## Required state matrix

Every touched route should be considered in these states:

- empty
- loading
- success
- long-content or stress
- error or fallback

If a route does not meaningfully support one of those states, say so explicitly instead of leaving the gap implicit.

## Allowed frontend task shapes

Keep frontend tasks in one of these shapes:

- shared contract or shell
- route slice
- validation
- review-fix

Avoid tasks that mix all of those at once. When a task spans multiple categories, split it or make the dependency story explicit.

## Closure rules

Do not close frontend implementation tasks until:

- required validation has passed on the final branch state
- the PR description is current
- the task notes include the PR number and final validation summary
- any deferred route work is represented explicitly in Beads

## Formula workflow

This repo ships a reusable formula for new frontend epics:

- `frontend-epic`

Useful commands:

```bash
bd formula list
bd formula show frontend-epic
bd cook frontend-epic --dry-run
bd mol pour frontend-epic \
  --var title="Close search and chat parity gaps" \
  --var goal="Bring the search route onto the shared shell and keep transcript overflow contained." \
  --var routes_in_scope="/agents/search, consultation rail" \
  --var routes_deferred="/agents/floor_plan_intake, /agents/image_analysis" \
  --var shared_contracts="shared agent shell, consultation rail overflow rules" \
  --var design_refs="design_references/stitch_design/, spec/uxui-march19/feedback.md"
```

The poured workflow gives you a reusable starting graph:

- a root epic with route matrix, non-goals, and validation placeholders
- a task to lock route coverage and deferred routes
- a task for implementation
- a task for validation, AGENTS updates, and PR reporting

Treat that graph as the starting point, not a substitute for thought. Rename tasks, split route slices, and add follow-up tasks where the actual work needs more resolution.

## Authoring rules for route-family work

- Do not use app-wide language unless every affected route family is actually covered.
- If home, navigation, or a single route is the only touched slice, say that in the epic.
- If a retrospective reframes existing open route work, update the original tasks or supersede them explicitly. Do not keep two active task graphs for the same missing work.
- If a route remains old on purpose, keep that visible in the epic and in the PR.

## Handoff note expectations

When pausing with an epic or task still open, add notes that record:

- what is already shipped on the branch
- what still blocks merge
- what was visually checked
- what remains visually unchecked
- what the next reviewer or implementer should verify first
