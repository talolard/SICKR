# UI Workspace Guidelines

Local instructions for work inside `ui/`. These rules refine the repo-wide guidance in the root `AGENTS.md` for the Next.js frontend.

## Scope

- `ui/` owns product-facing presentation, layout, interaction patterns, and browser-side state management.
- Keep business rules, parsing, and agent-specific state shaping in typed hooks or `ui/src/lib/*`, not inline inside JSX branches.
- Treat the UI as a product surface, not a debug console.

## Current stack

- Next.js App Router, React 19, TypeScript, Tailwind CSS v4.
- CopilotKit provides the chat runtime and baseline chat UI.
- Tool rendering is built around typed tool contracts and renderer components, with CopilotKit wiring the tool-call stream into React renderers.
- Floor-plan intake and preview depend on Three.js through `three`, `@react-three/fiber`, and `@react-three/drei`.
- We currently use lightweight custom styling on top of CopilotKit rather than a full component library.
- If a future change adds a shared component layer, document the reason and the allowed usage pattern here.

## Core rendering patterns

- Keep the typed tool-rendering pattern intact:
  - parse tool outputs into typed shapes
  - map those tool calls into renderer components
  - keep rendering concerns in the UI layer rather than leaking ad hoc formatting into backend payloads
- Preserve the `CopilotToolRenderers` / renderer-hook pattern unless there is a clear replacement plan.
- Keep structured outputs as first-class renderers, not raw JSON dumps or prose-only fallbacks.
- Preserve the floor-plan 3D preview path as a first-class product feature. Do not simplify it away into static screenshots just to make UI work easier.
- When touching 3D surfaces, prefer small presentation changes around the viewer before changing the scene/rendering architecture itself.

## UX priorities

- User-facing content comes first.
- Structured outputs such as bundles, product results, floor-plan previews, and 3D room surfaces are first-class work surfaces, not incidental chat decoration.
- Prompt text, runtime notes, and debug details are secondary by default and should not dominate the initial page layout.
- Prefer calm, stable layouts over clever or animated ones.

## Layout rules

- Every pane must have one explicit scroll owner.
- In flex or grid layouts, add `min-h-0` to any child expected to scroll.
- On agent pages with side-by-side workspace and chat rails, define an explicit desktop height boundary first, then assign scroll ownership within that boundary.
- Do not let transcripts, result lists, or nested cards expand page height unexpectedly.
- If content is long, constrain it and make the scroll region visually obvious.
- Keep pane boundaries readable. Do not rely on repeated light-gray boxes with nearly identical styling to create hierarchy.

## CopilotKit rules

- Start from CopilotKit defaults and override only what is necessary.
- Keep CopilotKit CSS overrides shallow and documented. If a selector is fragile or library-internal, add a short comment explaining why it exists.
- Do not take on chat-surface architecture changes casually. Inline chat, sidebar chat, and popup chat are product-level decisions and should be called out explicitly in plans.
- When structured outputs become primary artifacts, prefer promoting them into the main work area instead of only leaving them buried in the transcript.

## Information hierarchy

- Default views should emphasize:
  - the current task
  - the main output surface
  - the action the user can take next
- Secondary views may include:
  - known facts
  - agent details
  - prompt text
  - runtime notes
- If a section is primarily useful for debugging or implementation validation, default it closed or move it behind a secondary affordance.
- Prompt text, runtime configuration, and raw tool wiring details should usually live behind a labeled debug disclosure rather than in the default reading flow.

## Component guidance

- Prefer small shared wrappers or helper components for repeated panel, section-header, badge, and empty-state patterns.
- Avoid duplicating long Tailwind class strings across multiple feature components when a small shared presentation primitive would do.
- Prefer accessible, conventional interaction patterns over custom controls.
- When the current surface is a workspace switcher or launcher, prefer an intentional button-plus-menu or card treatment over browser-default selects if the default control reads as placeholder-level UI.
- Keep functions small and typed. Presentation components should receive already-shaped data whenever possible.

## Thread and state rules

- Thread creation and switching are product contracts, not incidental behavior.
- Thread switches must be deterministic and covered by tests on real agent pages.
- If a library behaves unreliably across live thread switches, prefer a stronger remount boundary over fragile state juggling.
- Persist rendered transcript state anywhere refresh or hydration continuity matters.

## Styling baseline

- Use Geist as the default UI font unless a deliberate alternative is introduced.
- Maintain consistent spacing, radius, border, and empty-state language across pages.
- Improve hierarchy with a small, reusable visual vocabulary rather than a bespoke design-system rewrite.
- Do not introduce a heavyweight UI library casually. If one is added, document:
  - why it is needed
  - which components are approved
  - what should still remain custom

## Testing expectations

- Add targeted tests for user-visible regressions.
- For layout fixes, assert behavior such as containment, visibility, scroll ownership, and interaction, not only snapshots.
- Prefer real-page Playwright coverage for:
  - thread creation and switching
  - chat containment
  - important navigation flows
- Keep component tests focused on rendering logic and affordances.
- When touching the floor-plan viewer or tool-rendering path, add or update focused tests around the affected renderer rather than relying only on broad page coverage.

## Validation

- UI work should normally run:
  - targeted `pnpm test` coverage for touched components
  - targeted Playwright coverage when behavior is user-visible
  - `make tidy`
- For behavioral changes on agent pages, aim to keep `make ui-test-e2e-real-ui-smoke` green before calling the work ready.
