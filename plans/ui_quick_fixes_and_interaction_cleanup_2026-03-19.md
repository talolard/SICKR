# UI Quick Fixes And Interaction Cleanup

## Summary

Tighten the current `ui/` experience with a focused quick-fixes epic that addresses the most obvious usability regressions, hierarchy problems, and product-polish gaps without taking on a full redesign.

This epic is intentionally incremental. It should stabilize the current CopilotKit + Tailwind app, raise the floor on visual quality, and leave room for later designer-driven direction changes.

Primary references:

- `spec/uxui-march19/feedback.md`
- `spec/uxui-march19/designer_review_brief.md`
- `ui/AGENTS.md`

## Why We Need This

The March 19 feedback surfaces a set of problems that are visible immediately:

- creating a new thread can freeze or no-op
- the search chat layout loses containment under long transcripts
- search results and bundles are hard to scan
- developer-facing information is too prominent
- navigation and launcher surfaces feel weak
- the visual baseline still reads as a prototype

These are not deep architectural bets. They are product bugs, layout bugs, and interaction hygiene issues that make the app feel more fragile and less usable than it needs to.

We want to fix the obvious issues now, while keeping the larger design language and chat-surface direction open for iteration with design.

## Goals

1. Create local UI guidance so future agents make consistent decisions inside `ui/`.
2. Fix thread creation and switching on real agent pages.
3. Restore bounded chat behavior and explicit scroll ownership in the search layout.
4. Make product results and bundles easier to scan without redesigning the whole renderer stack.
5. Demote debug-oriented material in the default layout.
6. Improve the launcher and agent-switching surfaces.
7. Establish a minimal but coherent visual baseline.
8. Add regression coverage so the current failures are hard to reintroduce.

## Non-Goals

This epic does not attempt to:

- replace the current inline chat with `CopilotSidebar` or `CopilotPopup`
- adopt a large new component library as a prerequisite
- perform a full information-architecture redesign
- overhaul every page in `ui/`
- block on final designer approval before fixing obvious regressions

## Core Design Decisions

### 1. Keep the current page architecture for this epic

The quick-fixes epic should stabilize the current layout rather than replace it.

Why:

- It keeps scope realistic.
- It preserves room to respond to the designer later.
- The biggest current pain points are containment and hierarchy, not the existence of the current page shells themselves.

### 2. Treat thread stability and chat containment as product bugs

Thread creation/switching and runaway transcript growth are not polish work. They are basic interaction contracts and should be fixed early.

Why:

- They directly undermine trust.
- They make follow-on UI work noisy and harder to verify.

### 3. Move internal material behind secondary affordances

Prompt text, runtime notes, and similar internal context should not compete with user-facing content in the default experience.

Why:

- The current first impression is too close to an internal tool.
- The product should foreground useful outputs and next actions.

### 4. Improve hierarchy with small shared patterns, not a design-system rewrite

This epic should introduce a tiny reusable visual vocabulary for panels, section headers, badges, and empty states where it helps.

Why:

- It reduces repeated one-off styling.
- It keeps the implementation cheap and incremental.
- It avoids prematurely committing to a heavyweight UI framework.

### 5. Keep CopilotKit overrides shallow

We should start from the library’s baseline behavior and only override what is necessary for containment, readability, and integration.

Why:

- Deep overrides increase fragility.
- Chat-surface architecture changes are better handled as explicit product decisions later.

### 6. Preserve the typed tool-rendering and 3D floor-plan patterns

This epic should improve the UI around the current rendering architecture rather than discard it.

Why:

- Tool rendering through CopilotKit-backed renderer components is already the app’s main pattern for structured outputs.
- Floor-plan intake and preview depend on the existing Three.js surface and should remain first-class.
- The quick-fixes epic should stabilize and polish these flows rather than flatten them into simpler but less capable UI.

## Task Breakdown

### Task 1: Add `ui/AGENTS.md`

Goal:

- Give future agents a local UI playbook so decisions stay consistent.

Reference:

- `spec/uxui-march19/feedback.md`

Scope:

- create `ui/AGENTS.md`
- codify local rules for layout, hierarchy, CopilotKit usage, tool-rendering patterns, Three.js floor-plan handling, state handling, styling, and tests

Verifiable outcome:

- `ui/AGENTS.md` exists and clearly instructs future agents how to work inside the UI workspace.

Dependencies:

- none

### Task 2: Stabilize thread creation and switching

Goal:

- Fix the `New thread` freeze or no-op behavior on real agent pages.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/app/CopilotKitProviders.tsx`
- `ui/src/app/agents/[agent]/agentPageHooks.ts`
- `ui/src/app/agents/[agent]/agentPageShell.tsx`
- real-page Playwright coverage

Decision:

- Treat thread switches as a strong state boundary. If needed, remount CopilotKit on thread changes instead of preserving fragile internal state through the transition.

Verifiable outcome:

- Clicking `New thread` on `/agents/search` creates a visibly new thread without freezing.
- Clicking `New thread` on `/agents/floor_plan_intake` creates a visibly new thread without freezing.
- Existing thread resume behavior still works.
- A real-page Playwright test covers the flow.

Dependencies:

- none

### Task 3: Fix chat containment and scroll ownership in the search layout

Goal:

- Keep the search chat column bounded and make transcript scrolling explicit.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/app/agents/[agent]/agentPageShell.tsx`
- `ui/src/components/copilotkit/AgentChatSidebar.tsx`
- `ui/src/components/copilotkit/renderers/shared.tsx` if needed

Decision:

- Keep inline chat for this epic.
- Make the right rail a bounded pane with one clear internal scroll region.

Verifiable outcome:

- The search page keeps a stable overall height.
- Transcript scroll stays inside the chat pane.
- Long assistant outputs do not push the full page into runaway vertical growth.
- Playwright coverage verifies containment against a realistic long-output case.

Dependencies:

- Task 2

### Task 4: Improve product-result readability inside chat

Goal:

- Make search results inside the transcript easier to skim and less visually overwhelming.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/components/tooling/ProductResultsToolRenderer.tsx`
- `ui/src/components/catalog/ProductImageThumbnail.tsx` if needed
- `ui/src/components/copilotkit/renderers/shared.tsx` if needed

Decision:

- Keep results collapsible.
- Make the header denser and more informative.
- Reduce description prominence.
- Make prices and counts faster to scan.

Verifiable outcome:

- Product result groups are easier to skim.
- Expand/collapse affordances are clearer.
- Long result sets remain contained.
- Component coverage asserts collapse and bounded scrolling behavior.

Dependencies:

- Task 3

### Task 5: Strengthen bundle hierarchy and affordances

Goal:

- Make bundles clearly separable, collapsible, and comparable.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/components/search/SearchBundlePanel.tsx`
- `ui/src/components/search/BundleProposalSummaryCard.tsx`

Decision:

- Bundle headers should read like headers, not generic cards.
- The active or selected bundle should be visually obvious.
- Expand/collapse cues should not rely on subtle text alone.

Verifiable outcome:

- A user can distinguish bundle summary from bundle detail at a glance.
- The active bundle is visually obvious.
- Expand/collapse is clearly discoverable.
- Bundle cards remain compact enough for multi-bundle scanning.

Dependencies:

- Task 8 preferred first for shared visual baseline
- Task 3 helpful but not strictly required

### Task 6: Move dev-oriented inspector content behind a secondary affordance

Goal:

- Reduce the internal-tool feel without losing access to useful debug information.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/components/agents/AgentInspectorPanel.tsx`
- `ui/src/app/agents/[agent]/agentPageShell.tsx`

Decision:

- Keep `Known facts` user-facing.
- Move prompt text and runtime notes behind a collapsed `Agent details` or `Debug` section.
- Default that section closed.

Verifiable outcome:

- Default agent pages foreground useful user context.
- Prompt and runtime details no longer dominate the first impression.
- Existing debug information remains accessible.

Dependencies:

- Task 8 preferred first for shared visual baseline

### Task 7: Polish navigation and the choose-agent entry surface

Goal:

- Make it clearer where to go and which agent to choose.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/components/navigation/AppNavBanner.tsx`
- `ui/src/app/page.tsx`
- `ui/src/app/agents/page.tsx`

Decision:

- Keep the current navigation structure.
- Improve the current agent selector state, loading behavior, and prominence.
- Make the home page feel like a launcher instead of a placeholder.

Verifiable outcome:

- The agent selector has loading and disabled handling.
- The current agent state is clearer.
- Agent cards are more intentional and informative.
- The landing page better explains the available workflows.

Dependencies:

- Task 8 preferred first for shared visual baseline

### Task 8: Establish a minimal visual baseline

Goal:

- Fix the most obvious prototype-level visual issues without introducing a full component system.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/src/app/globals.css`
- `ui/src/app/layout.tsx`
- small shared presentation wrappers or style helpers

Decision:

- Use Geist properly as the default UI font.
- Replace Create Next App metadata.
- Introduce a tiny shared visual language for panels, section headers, badges, and empty states.
- Do not block this task on adopting `shadcn/ui`.

Verifiable outcome:

- Typography is consistent.
- Metadata is no longer boilerplate.
- Main app surfaces share more coherent spacing, border, radius, and empty-state treatment.
- Empty and loading states look intentional rather than raw.

Dependencies:

- none

### Task 9: Add real-page regression coverage for the quick fixes

Goal:

- Make the current failures hard to reintroduce.

Reference:

- `spec/uxui-march19/feedback.md`

Expected scope:

- `ui/e2e/real-backend.spec.ts` or a new real-page spec
- targeted component tests where useful

Must cover:

- new thread does not freeze
- search chat remains bounded under long content
- bundle expand/collapse still works
- inspector default state matches the intended hierarchy
- agent picker interaction does not regress

Verifiable outcome:

- The behaviors above are exercised on real agent pages, not only the debug harness.

Dependencies:

- Tasks 2 through 8

## Sequencing

Recommended order:

1. Task 1: add `ui/AGENTS.md`
2. Task 2: stabilize thread creation and switching
3. Task 3: fix chat containment and scroll ownership
4. Task 8: establish a minimal visual baseline
5. Task 4: improve product-result readability
6. Task 5: strengthen bundle hierarchy and affordances
7. Task 6: move dev-oriented inspector content behind a secondary affordance
8. Task 7: polish navigation and the choose-agent entry surface
9. Task 9: add regression coverage sweep

## Deliverables

- `ui/AGENTS.md`
- fixes to thread creation and switching on real agent pages
- bounded search chat containment
- improved in-chat product result readability
- clearer bundle summary and detail hierarchy
- demoted debug-oriented inspector content
- improved launcher and agent-switching surfaces
- a minimal shared visual baseline
- targeted regression coverage for the quick fixes

## Acceptance Criteria

- `ui/AGENTS.md` exists and captures the local UI rules future agents should follow.
- Creating a new thread works on the real agent pages without freezing the UI.
- Search chat and long search outputs stay visually bounded.
- Product results and bundles are materially easier to scan than before.
- The default agent page foregrounds user-facing content over prompt/runtime internals.
- The launcher and agent-switching surfaces feel intentional rather than placeholder-level.
- The visual baseline is more coherent without requiring a heavy new UI framework.
- Regression coverage exists for the main failures surfaced in the March 19 feedback.

## Explicit Review Gate

Before expanding this epic into larger architectural changes, pause for design review on:

- whether inline chat remains the right long-term surface
- whether a lightweight component layer is enough or a broader UI system is warranted
- whether the launcher and multi-agent model should evolve into a different product structure

This quick-fixes epic should improve the current experience, not lock in the final design direction.
