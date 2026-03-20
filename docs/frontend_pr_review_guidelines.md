# Frontend PR Review Guidelines

Operational guidance for authoring and reviewing frontend pull requests.

Use this for both sides of the PR process:

- authors should use it to shape the PR description
- reviewers should use it to decide whether the branch is honest about scope and ready to merge

## What every frontend PR description must include

- Summary:
  - what user-visible change landed
- Routes covered:
  - the exact routes and surfaces touched by the branch
- Routes deferred:
  - the exact sibling routes intentionally left unchanged
- Shared contracts affected:
  - shared shells, rails, renderers, or interaction rules
- Design references checked:
  - exact screenshots, exported HTML, or design docs
- Beads tasks closed in this PR
- Beads tasks intentionally left open
- Validation:
  - manual checks and automated checks
- Remaining risks:
  - what still needs follow-up or explicit caution

## Rules for PR authors

- If the PR only covers one slice of a broader epic, say that in the first paragraph.
- If a review-fix pass does not change route coverage, say that explicitly.
- If the branch changes chat or tool-rendering UI, mention long-content and raw-payload behavior explicitly.
- If the branch follows a squash-merged predecessor, cut the follow-up branch from `main` or cherry-pick the new commits so the commit list stays reviewable.
- Do not describe local fidelity improvements as route-family parity unless the sibling routes were also updated and checked.

## Reviewer checklist

Reviewers should be able to answer these questions explicitly:

1. Which routes are actually covered by this PR?
2. Which sibling routes remain intentionally old or incomplete?
3. Does the PR touch a shared shell or only a local slice?
4. If it touches only a local slice, does the PR description avoid app-wide claims?
5. Were the touched routes compared against named design references?
6. Were fresh-thread, existing-thread, success, and long-content states checked?
7. If CopilotKit or transcript styling changed, were scroll ownership and long raw payload behavior checked?
8. Are the Beads tasks and PR body synchronized about what is done versus deferred?
9. If the branch follows a squash-merged predecessor, is the commit history still reviewer-friendly?

## Required validation for route-family work

For route-family or shared-shell work, the manual check should always include:

- one canonical desktop viewport
- one fresh thread
- one existing thread
- one realistic success path
- one long-content or raw-tool-output stress case

Automated checks should normally include:

- targeted Vitest coverage for touched components or renderers
- targeted Playwright coverage when the behavior is user-visible
- `make tidy`
- `make ui-test-e2e-real-ui-smoke` when agent-page behavior changed

## Review workflow formula

This repo ships a reusable frontend review formula:

- `frontend-pr-review`

Recommended usage is as a wisp:

```bash
bd formula show frontend-pr-review
bd mol wisp frontend-pr-review \
  --var title="Review frontend PR #72: Close Stitch rollout gaps in the agent workspaces" \
  --var pr_number=72 \
  --var pr_title="Close Stitch rollout gaps in the agent workspaces" \
  --var routes_claimed="home, search workspace, floor-plan intake workspace, image-analysis workspace, consultation rail" \
  --var design_refs="design_references/stitch_design/, spec/uxui-march19/report.md" \
  --var author_validation="make tidy; make ui-test-e2e-real-ui-smoke"
```

Use the review wisp to track:

- route coverage honesty
- design-reference fidelity
- state and stress checks
- validation evidence
- findings or approval outcome

If the review finds real blocking issues:

```bash
bd create "Fix consultation rail horizontal overflow" -t task -p 1 \
  --deps discovered-from:<review-id>
bd dep add <review-id> <new-issue-id> --type blocks
```

That keeps ephemeral review work separate from durable implementation follow-ups.
