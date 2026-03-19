# Stitch Editorial Redesign Mapping

Date: 2026-03-19

## Goal

Adopt the visual language and interaction tone from `design_references/stitch_design/` across the `ui/` workspace without replacing the underlying runtime architecture. The new look should read as an editorial interior-design studio, while preserving the current typed React, CopilotKit, and AG-UI patterns that already work.

This plan is for a follow-on redesign branch after `tal_maria_ikea-mi4`, not a wholesale rewrite from scratch.

Implementation rule:

- Update local UI guidance when it conflicts with Stitch rather than trying to preserve older styling rules alongside the new system.

## Source Artifacts

- `design_references/stitch_design/DESIGN.md`
- `design_references/stitch_design/home_screen/code.html`
- `design_references/stitch_design/floor_screen/code.html`
- `design_references/stitch_design/home_screen/screen.png`
- `design_references/stitch_design/floor_screen/screen.png`

## Design Read

### Creative direction

- The intended identity is "The Digital Curator": editorial authority plus domestic warmth.
- The pages should feel composed, asymmetrical, and spacious rather than dashboard-like.
- The current MI4 UI already improved stability and hierarchy, but it still reads as a polished product workspace. The Stitch reference is aiming for a softer magazine/studio tone.

### Visual system rules that matter

- Warm neutral base with deep forest green and restrained terracotta accenting.
- Serif display type paired with a clean sans utility face.
- Tonal layering is the primary hierarchy tool.
- Rounded shapes everywhere; no sharp corners.
- Floating or glassy chrome for top-level navigation and active AI surfaces.
- Chips, CTAs, and FABs should feel tactile rather than flat.

### Source conflict to resolve deliberately

The exported HTML does not perfectly obey the prose rules in `DESIGN.md`.

- `DESIGN.md` says borders should be avoided for sectioning and containment.
- The exported HTML still uses many `border-*` classes for nav selection, rails, canvas framing, and chat bubbles.

Implementation rule:

- Treat `DESIGN.md` as the source of truth for system principles.
- Treat `code.html` and screenshots as composition references, spacing references, and copy/tone references.
- Where accessibility or component clarity requires a stroke, use the "ghost border" fallback sparingly and at low contrast.

## Current UI Architecture To Preserve

The redesign should preserve these implementation patterns:

- `ui/src/app/layout.tsx` owns global fonts, metadata, and CopilotKit stylesheet bootstrapping.
- `ui/src/app/globals.css` is the right place for workspace-wide tokens, CSS variables, and low-level shared utility classes.
- `ui/src/components/navigation/AppNavBanner.tsx` is the top-shell navigation seam.
- `ui/src/app/page.tsx` and `ui/src/app/agents/page.tsx` are launcher surfaces.
- `ui/src/app/agents/[agent]/agentPageShell.tsx` owns the major shell composition for search and floor-plan pages.
- `ui/src/components/agents/AgentInspectorPanel.tsx` is the existing left-rail content seam.
- `ui/src/components/copilotkit/AgentChatSidebar.tsx` and transcript/tool renderers own the right-rail consultation/chat experience.
- `ui/src/components/search/*` and `ui/src/components/tooling/*` are the correct seams for bundle and product result redesigns.

The redesign should not copy the exported HTML directly into the app. The right move is to translate it into reusable primitives and then wire those into the existing page composition.

## Mapping The Stitch Design To Our UI

### 1. Theme foundation

Reference intent:

- Noto Serif display
- Plus Jakarta Sans utility text
- warm editorial palette
- tonal surfaces instead of border-heavy cards

Implementation mapping:

- Update `ui/src/app/layout.tsx` to load `Noto_Serif` and `Plus_Jakarta_Sans` with `next/font/google`.
- Replace the current Geist-first workspace baseline in `ui/src/app/globals.css` with editorial token variables.
- Define semantic tokens, not page-local color literals:
  - `--surface`
  - `--surface-low`
  - `--surface-lowest`
  - `--surface-high`
  - `--surface-highest`
  - `--primary`
  - `--primary-container`
  - `--secondary`
  - `--secondary-container`
  - `--text-primary`
  - `--text-muted`
  - `--outline-ghost`
- Add shared utility classes for:
  - glass nav
  - tonal panel
  - elevated card
  - editorial eyebrow
  - serif headline
  - pill chip
  - gradient CTA

### 2. Top navigation and global chrome

Reference intent:

- fixed glass nav
- understated brand wordmark
- fewer hard boxes
- current section shown through typography and subtle underline

Implementation mapping:

- Redesign `ui/src/components/navigation/AppNavBanner.tsx` into the glass editorial header.
- Keep the existing router-driven workspace switcher behavior, but render it as a curated-menu interaction instead of the current utility dropdown card.
- Move the current active-workspace explanation into softer helper copy rather than a blocky launcher panel.
- Preserve loading and error states from MI4; only the presentation changes.

### 3. Launcher and home page

Reference intent:

- editorial hero
- large serif heading
- three curated entry points with image-led cards
- archive/recent work section below

Implementation mapping:

- Rework `ui/src/app/page.tsx` and `ui/src/app/agents/page.tsx` to use the Stitch-style hero and card composition.
- Expand `ui/src/components/agents/AgentLauncherCard.tsx` into an image-forward editorial card primitive.
- Do not hardcode the remote reference images from the exported HTML.
- Use repo-local assets, neutral placeholders, or agent-specific illustration blocks until a product-approved image source exists.
- Keep the card behavior simple: current repo only needs to route into workspaces; "archives" can be presentational or driven by existing data if available.

### 4. Left rail: context instead of inspector

Reference intent:

- a persistent contextual sidebar
- section list plus selected context details
- strong but quiet hierarchy

Implementation mapping:

- Convert `ui/src/components/agents/AgentInspectorPanel.tsx` from an inspector panel into a context rail.
- Keep the same underlying data:
  - known facts
  - metadata
  - relevant constraints
- Reframe debug content as deeply secondary and probably hidden behind a final disclosure at the bottom.
- For search and floor-plan pages, the left rail should feel like "project specifications" or "room specifications", not developer metadata.

### 5. Right rail: consultation instead of generic chat

Reference intent:

- the right rail reads like an active design consultation
- suggestions appear as tactile chips
- composer is soft, embedded, and conversational

Implementation mapping:

- Restyle `ui/src/components/copilotkit/AgentChatSidebar.tsx` and related CopilotKit overrides around the existing transcript runtime.
- Keep current scroll ownership and bounded height rules from MI4.
- Introduce:
  - editorial chat heading
  - softer bubble treatments
  - pill suggestions
  - warmer composer styling
- Do not change the underlying conversation model or thread persistence behavior in this redesign pass.

### 6. Search workspace

Reference intent:

- central workspace is the primary stage
- results feel curated rather than dumped
- chat is consultation, not a second competing application

Implementation mapping:

- Keep `ui/src/app/agents/[agent]/agentPageShell.tsx` as the shell owner.
- Introduce editorial shell primitives there:
  - glass header
  - contextual left rail
  - central work surface
  - softer right consultation rail
- Redesign:
  - `ui/src/components/tooling/ProductResultsToolRenderer.tsx`
  - `ui/src/components/search/SearchBundlePanel.tsx`
  - `ui/src/components/search/BundleProposalSummaryCard.tsx`
- Bundle and product surfaces should move from bordered utility cards toward layered tonal cards with stronger typographic grouping.

### 7. Floor-plan workspace

Reference intent:

- architectural workbench in the center
- floor plan shown like a drafting surface
- lightweight toolbar above
- explicit finalize action as a floating CTA

Implementation mapping:

- Keep `ui/src/app/agents/[agent]/agentPageShell.tsx` as the shell owner for the floor-plan route.
- Preserve the existing floor-plan preview architecture and canvas integration.
- Wrap the viewer in a drafting-stage frame inspired by the reference:
  - quiet grid or drafting background
  - concise top toolbar
  - floating AI status chip
  - floating finalize CTA
- Any changes to the actual 3D/floor-plan renderer should be avoided unless needed to support the framing.

### 8. Motion and loading

Reference intent:

- soft motion
- breathing or pulsing status instead of generic spinners

Implementation mapping:

- Replace generic loading indicators in the launcher and agent pages with pulse or shimmer blocks consistent with the editorial palette.
- Keep motion restrained and purposeful.

## Component Strategy

Add a small editorial presentation layer rather than scattering one-off Tailwind strings everywhere.

Recommended new component areas:

- `ui/src/components/chrome/EditorialTopNav.tsx`
- `ui/src/components/chrome/EditorialRailSection.tsx`
- `ui/src/components/chrome/EditorialPanel.tsx`
- `ui/src/components/chrome/EditorialBadge.tsx`
- `ui/src/components/chrome/EditorialActionChip.tsx`

These should remain thin presentation primitives. Existing product components should keep their typed data contracts.

## Copy Strategy

The Stitch reference uses warmer, more editorial copy:

- "Designer's Studio"
- "Design Consultation"
- "Room Specifications"
- "The Archives"

We should adopt that tone selectively:

- Good candidates:
  - page titles
  - section headers
  - helper copy
  - empty states
- Avoid changing backend agent names or protocol-facing IDs.

User-facing labels should still come from typed frontend metadata or helper functions rather than ad hoc string assembly in JSX.

## Risks And Constraints

- The redesign must not regress the MI4 thread-creation and bounded-scroll fixes.
- CopilotKit overrides must stay shallow enough to survive upstream updates.
- The exported HTML is static and marketing-oriented; our real UI has dynamic data, error states, tool output volume, and attachments.
- Search pages and floor-plan pages should share an editorial family, but not become visually identical.
- Do not introduce a heavyweight UI component library just to mimic the reference.

## Validation Expectations

The redesign work should keep these checks green:

- targeted Vitest coverage for touched components
- `pnpm typecheck`
- `make ui-test-e2e-real-ui-smoke`
- real-page Playwright coverage for:
  - launcher navigation
  - new-thread behavior
  - bounded chat/transcript behavior
  - bundle interactions
  - floor-plan consultation shell

## Proposed Work Breakdown

1. Establish editorial theme tokens, fonts, and low-level shared presentation primitives.
2. Rebuild top navigation and launcher/home surfaces in the Stitch style.
3. Reframe the shared agent shell into left-context, center-workspace, right-consultation composition.
4. Redesign search results and bundles within that shell.
5. Redesign the floor-plan page framing, toolbar, status, and CTA treatment.
6. Restyle the CopilotKit consultation rail, composer, and suggestion affordances.
7. Expand component and real-page regression coverage around the redesigned surfaces.

## PR Shape Recommendation

Do not land the entire redesign as one giant styling dump.

Recommended stack:

1. theme foundation and chrome primitives
2. home and launcher surfaces
3. shared shell and context rail
4. search workspace redesign
5. floor-plan workspace redesign
6. consultation rail and regression coverage

This keeps behavior verification tractable and reduces the chance of losing the MI4 stability work inside a visual rewrite.
