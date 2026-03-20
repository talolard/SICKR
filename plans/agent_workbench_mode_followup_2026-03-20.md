# Agent Workbench Mode Follow-Up

Date: 2026-03-20

## Scope

- Touched routes:
  - `/agents/search`
  - `/agents/floor_plan_intake`
  - `/agents/image_analysis`
  - consultation rail tool/result rendering on agent pages
- Deferred routes:
  - `/`
  - launcher/home chrome except regressions directly caused by shared-shell changes

## References

- `spec/uxuimarch20/feedback.md`
- `spec/uxuimarch20/headerspace.png`
- `spec/uxuimarch20/bundledisplay.png`
- `spec/uxuimarch20/searchcard.png`
- `spec/uxuimarch20/screenshots/home_screen_columns_not_aligned.png`
- `design_references/stitch_design/DESIGN.md`
- `ui/src/app/agents/[agent]/agentPageShell.tsx`
- `ui/src/components/agents/workspacePresentation.ts`
- `ui/src/components/thread/ThreadDataPanel.tsx`
- `ui/src/components/search/SearchBundlePanel.tsx`
- `ui/src/components/search/BundleProposalSummaryCard.tsx`
- `ui/src/components/tooling/ProductResultsToolRenderer.tsx`
- PR `#78` / commit `1ecfd8a`

## Validated findings on current `main`

### 1. Agent page headers are still too tall

Validated as a real current issue.

The shared shell still spends too much of the first screenful on framing before the user reaches the live work surface:

- `AgentThreadHeader` stacks capability pills, a large serif route title, descriptive copy, thread controls, warnings, and `ThreadDataPanel` inside one tall header card.
- The result matches the feedback screenshot: active-thread routes make the user scroll before the main artifact becomes visible.

### 2. Search still duplicates vertical section framing

Validated as a real current issue.

The search route currently renders:

1. the shared stage card in `agentPageShell`
2. the `SearchBundlePanel` heading block
3. the bundle summary card itself

That means the route spends two large cards on labels before the first real bundle artifact.

### 3. Search result summaries in the consultation rail are still too tall

Validated as a real current issue.

`ProductResultsToolRenderer` still uses a generous card treatment that is too large for the narrow rail:

- eyebrow
- multi-line title
- separate badge row
- separate expand/collapse pill
- large padding around the card

This remains visually polished but operationally too dense for a 300px-ish rail.

### 4. Success-state validation pills are still louder than the content

Validated as a real current issue.

`SearchBundlePanel` renders every validation as a colored pill, including successful checks. The feedback is correct that these draw disproportionate attention relative to bundle title, price, and included products.

### 5. The expanded bundle view still adds an extra “Included items” framing block

Validated as a real current issue.

Expanded bundle details still insert an “Included items” title plus subtitle before the actual rows. That adds another framing layer after the summary card and validation pills instead of moving directly into comparable item data.

### 6. The home-screen alignment issue is not a remaining blocker

Validated as largely addressed by PR `#78`, so it should not drive the new implementation epic.

Current code now:

- enforces a deterministic card order in `StudioShowcaseLayout`
- removes the white in-image title box treatment in `AgentLauncherCard`
- uses a simpler right-rail treatment
- bottom-pins the CTA row with `mt-auto`

The March 20 workbench follow-up should stay focused on agent routes and consultation density, not reopen the home slice.

## Design adjustment

The feedback is pointing at a real system-level mistake: we applied the Stitch editorial language as if all routes deserved the same density.

The fix is not to abandon the redesign. The fix is to codify one visual system with two density modes:

- Editorial mode:
  - home
  - onboarding
  - empty states
  - large marketing or invitation surfaces
- Workbench mode:
  - active-thread agent pages
  - dense result lists
  - bundle comparison surfaces
  - narrow consultation rails

Shared palette, typography, and tonal layering should stay consistent across both modes. The density rules should not.

## Implementation strategy

### 1. Compact the shared agent shell

Targets:

- `ui/src/app/agents/[agent]/agentPageShell.tsx`
- `ui/src/components/agents/workspacePresentation.ts`
- `ui/src/components/thread/ThreadDataPanel.tsx`

Direction:

- collapse active-thread headers into a compact workbench bar
- keep the route identity, thread selector, and next action visible on the first screen
- demote descriptive copy and thread metadata into quieter secondary regions or disclosures
- do not render multiple large heading cards before the first workspace artifact

### 2. Flatten the search workbench hierarchy

Targets:

- `ui/src/components/search/SearchBundlePanel.tsx`
- `ui/src/components/search/BundleProposalSummaryCard.tsx`
- search-stage composition in `agentPageShell`

Direction:

- remove or collapse duplicate section cards
- let the first bundle card appear immediately after a compact header
- keep price, item count, and the next available action visually stronger than explanation text
- integrate item rows directly into the expanded bundle rather than adding another hero-like subheader

### 3. Rebuild narrow-rail search summaries as compact list items

Target:

- `ui/src/components/tooling/ProductResultsToolRenderer.tsx`

Direction:

- switch from feature-card treatment to compact summary rows
- keep title/query, result count, and expand control on one tight block
- reserve the larger product-card treatment for expanded content or the main workspace

### 4. Change status semantics so success is quiet

Targets:

- `ui/src/components/search/SearchBundlePanel.tsx`
- any shared badge/status primitives used by the route

Direction:

- hide or heavily demote pass-state validation by default
- keep warning and failure states visually prominent
- prefer inline checks or a secondary details disclosure for “everything is fine” metadata

### 5. Verify the same density rules on floor-plan and image-analysis

Targets:

- shared shell and route-specific workspace framing

Direction:

- keep the existing route family consistent
- do not let search become compact while floor-plan and image-analysis stay oversized
- preserve each route’s center-surface identity while sharing header density and chrome budget rules

## Guidance updates required

- `ui/AGENTS.md`:
  - define editorial mode vs workbench mode explicitly
- `docs/frontend_delivery_guidelines.md`:
  - add surface-mode planning and workbench validation rules
- `docs/frontend_epic_authoring.md`:
  - require surface-mode and above-the-fold artifact expectations in epics/tasks
- `docs/frontend_pr_review_guidelines.md`:
  - require reviewers to check chrome budget, quiet-success semantics, and narrow-rail density

## Acceptance checks for the implementation phase

- An active-thread agent route shows route identity, thread controls, and the first primary artifact within the first screenful at the canonical desktop viewport.
- Search no longer stacks two large section cards before the first bundle.
- Consultation-rail search summaries read as compact transcript artifacts rather than standalone feature cards.
- Success-state validation no longer pulls focus ahead of prices, product names, or actions.
- Floor-plan and image-analysis follow the same shared density rules without losing their route-specific center work surfaces.
