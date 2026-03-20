# Frontend Delivery Guidelines

Guidance for planning, implementing, and validating frontend work in `tal_maria_ikea`.

This exists because the March 2026 UI work exposed a few repeated failure modes:

- a redesign slice can look complete on one route while the route family is still inconsistent
- layout bugs often come from unclear scroll ownership and third-party DOM assumptions
- chat and tool surfaces can degrade quickly under long text, raw JSON, and large structured outputs
- component tests alone are not enough for route-level UX work

## Planning checklist

Before editing UI code, write down:

- the exact routes being changed
- the exact routes intentionally not being changed
- the design artifacts used as references
- the states that must look correct:
  - empty
  - loading
  - success
  - long-content / stress
  - error or fallback
- the user-visible acceptance checks for each touched route

For redesign work, do not use app-wide language unless all routes in the relevant family are covered.

## Execution order

Prefer this order for non-trivial frontend work:

1. Define the shared layout contract first.
2. Decide scroll ownership and desktop/mobile height boundaries.
3. Move primary artifacts into the main workspace if they should not live only in chat.
4. Add route-specific copy and presentation metadata.
5. Add route-local polish only after the shared shell is correct.
6. Add targeted tests and real-page verification before merge.

If multiple routes should feel like one product family, implement the shared shell before route-specific embellishment.

## Shared-shell rules

- Treat route-family consistency as a product requirement.
- Shared layout grammar should live in shared shells and shared presentation helpers, not duplicated page-local class strings.
- Route-specific differences should usually be expressed through:
  - copy
  - badges
  - panel contents
  - route-specific center-surface components
- Do not let one route silently invent a different page grammar unless that difference is a deliberate product decision.

## Chat and tool-rendering rules

- The consultation rail is a product surface, not a raw CopilotKit dump.
- Primary work artifacts should move into the main workspace when they need sustained attention.
- Bulky structured outputs inside the chat rail should default collapsed unless always-expanded behavior is clearly better.
- Raw tool output must not cause horizontal overflow in the chat rail.
- Long strings, JSON, code-ish payloads, and markdown should wrap safely inside narrow columns.
- Assistant controls must remain visually attached to the message they belong to.
- When overriding third-party chat UI, inspect the real DOM first instead of assuming the library structure.

## Scroll and overflow rules

- Every pane must have one explicit scroll owner.
- In nested flex or grid layouts, add `min-h-0` to children that are expected to scroll.
- Do not leave multiple nested elements competing for vertical scrolling unless that is intentional and tested.
- Stress-test overflow with:
  - long assistant prose
  - long unbroken strings
  - raw JSON
  - large result groups
  - repeated tool cards
- If a layout fix depends on overflow behavior, verify it on the live page instead of relying only on static reasoning.

## Third-party UI override rules

- Start with the smallest override that gives the product behavior you need.
- Prefer shallow selectors.
- If a selector depends on library internals, document why it exists.
- Reproduce the issue in the running app before changing third-party overrides.
- Re-check the actual computed layout after the change. DOM structure matters more than assumptions.

## Validation protocol

For meaningful frontend work, validate in layers:

1. targeted component tests for the touched renderer or panel
2. targeted route or Playwright checks for user-visible behavior
3. manual visual review on the running app
4. full repo gate with `make tidy`
5. deferred route-level smoke in CI when agent-page behavior changed; that lane now waits for `PR CI` and `Dependency Review` to succeed for the PR SHA, and `make ui-test-e2e-real-ui-smoke` is local debug-only

During manual review, check at least:

- a fresh thread
- an existing thread
- one realistic successful interaction
- one stress case with long content
- the touched route at the canonical desktop width used by the reference

## PR and merge expectations

Frontend PRs should say explicitly:

- which routes were touched
- which routes were deferred
- which design references were checked
- what manual visual verification was performed
- what automated checks were run

If the work only covers home, theme, or navigation, the PR should say that directly and avoid implying full route-family parity.

## Recommended pace

For faster delivery, avoid big speculative passes. Use short loops:

1. inspect the live route
2. patch the shared contract or renderer
3. re-open the live route
4. verify the exact failure mode is gone
5. only then broaden the polish

That is usually faster than doing a broad styling sweep and discovering overflow, transcript, or route-family regressions at the end.
