# UI Retrospective: PRs #70 and #71

Date: 2026-03-20

## Reviewed artifacts

- User screenshots from 2026-03-20 showing the current home, floor-plan, image-analysis, and chat surfaces
- `design_references/stitch_design/DESIGN.md`
- `design_references/stitch_design/home_screen/DESIGN.md`
- `design_references/stitch_design/home_screen/code.html`
- `design_references/stitch_design/floor_screen/DESIGN.md`
- `design_references/stitch_design/floor_screen/code.html`
- PR `#70` and PR `#71`, including PR `#71` follow-up comments
- Current UI code in:
  - `ui/src/app/agents/[agent]/agentPageShell.tsx`
  - `ui/src/components/agents/AgentInspectorPanel.tsx`
  - `ui/src/components/copilotkit/AgentChatSidebar.tsx`
  - `ui/src/components/navigation/AppNavBanner.tsx`
  - `ui/src/components/agents/StudioShowcaseLayout.tsx`
  - `ui/src/components/agents/AgentLauncherCard.tsx`

## Executive summary

- PR `#70` did what it claimed: a March 19 stabilization and polish pass. It explicitly did not take on a broader redesign.
- PR `#71` imported the Stitch reference pack and shipped a first editorial slice for theme, navigation, and home/launcher surfaces.
- The shared agent workspace shell was not migrated in PR `#71`. The core files that still drive floor-plan intake, image analysis, and the generic consultation chat rail remained unchanged from the PR `#70` state.
- The result is a split UI: the home surface moved toward Stitch, while the live workspaces stayed on the older MI4 bordered shell.
- The main process failure was not a single bad implementation decision. It was scope blur: the design system plan, epic definition of done, PR framing, and review attention were not aligned tightly enough around which routes were actually expected to match the reference before merge.

## What the design expected

The Stitch references establish a consistent product family:

- Home uses the editorial hero, composed card spread, contextual left rail, and lightweight consultation rail.
- Agent workspaces use a left-context / center-workspace / right-consultation composition.
- The floor-plan screen is an architectural workbench, with room specifications on the left, a drafting-style central surface, and a design-consultation rail on the right.
- The image-analysis page should read as the same product family as floor-plan and search, not as a separate utility page.
- The system-wide rules are clear:
  - use tonal layering instead of explicit containment borders
  - keep the product warm and editorial rather than dashboard-like
  - treat AI chat as consultation, not as a generic developer sidebar

## What actually shipped

### PR #70

PR `#70` explicitly scoped itself to quick fixes and baseline polish:

- thread creation and switching stability
- bounded chat containment
- readability fixes for search results and bundles
- demotion of debug-heavy inspector content
- launcher/navigation polish
- a modest visual baseline

This matched the code that landed.

### PR #71

PR `#71` explicitly shipped:

- Stitch reference import and mapping
- global editorial tokens and fonts
- top navigation redesign
- home / launcher redesign
- follow-up review fixes focused on theme fidelity and home composition

Between the PR `#70` merge commit and the current `main` tip from PR `#71`, the affected UI diff is concentrated in:

- `ui/src/app/globals.css`
- `ui/src/app/page.tsx`
- `ui/src/app/agents/page.tsx`
- `ui/src/components/navigation/AppNavBanner.tsx`
- `ui/src/components/agents/AgentLauncherCard.tsx`
- `ui/src/components/agents/StudioShowcaseLayout.tsx`

The shared workspace files below did not move in that slice:

- `ui/src/app/agents/[agent]/agentPageShell.tsx`
- `ui/src/components/agents/AgentInspectorPanel.tsx`
- `ui/src/components/copilotkit/AgentChatSidebar.tsx`

That explains the current state in the screenshots.

## Current product problems

### 1. Floor-plan intake does not match the Stitch floor-screen reference

Observed now:

- The page still uses the older bordered MI4 shell with a utility-style header, bordered preview panel, bordered upload panel, and generic chat sidebar.
- The Stitch floor-screen reference expects:
  - a quieter room-specifications rail
  - a composed central workbench
  - a consultation rail labeled `Design Consultation`
  - a stronger drafting/workbench feeling
  - a more intentional finalization/action treatment

Root cause:

- The shared agent shell was never included in the PR `#71` implementation slice.
- The floor-plan route is still rendered by the same `agentPageShell.tsx` and `AgentChatSidebar.tsx` that shipped in PR `#70`.

Corrective action:

- Redesign the shared agent shell first.
- Then add floor-plan-specific framing on top of that shell instead of continuing to patch the old utility composition.

### 2. Image-analysis is not baseline-consistent with the other agent pages

Observed now:

- The image-analysis page uses the same older shell but lands with a different visual rhythm and content stacking than the floor-plan page.
- The result is not a consistent product family. It feels like a route-specific variation without a common design grammar.

Root cause:

- No route-by-route parity gate existed for non-home pages.
- The Stitch rollout focused on shared theme and home surfaces, while image-analysis never received an explicit parity task in the merged slice.

Corrective action:

- Make image-analysis a first-class redesign target with a clear baseline contract:
  - same shell family
  - same typography and surface hierarchy
  - route-specific content only inside the center workspace

### 3. The chat rail still looks and behaves like generic CopilotKit UI

Observed now:

- The chat surface still shows the bordered, utility-style container and composer.
- The message controls in the transcript can crowd the lower edge of assistant messages.
- The consultation rail design from Stitch was not applied.

Root cause:

- PR `#70` explicitly avoided a chat-surface rewrite.
- PR `#71` did not revisit `AgentChatSidebar.tsx`.
- Review attention on PR `#71` stayed focused on the home slice rather than the live workspace consultation rail.

Corrective action:

- Redesign the consultation rail and composer as part of the shared workspace shell work.
- Add route-level regression coverage for chat containment and message-control positioning.

### 4. The home screen still has composition and alignment drift

Observed now:

- The main page is closer to the Stitch direction, but the screenshot still shows visible layout drift from the reference.
- The page reads as a good reinterpretation rather than a settled product baseline.

Root cause:

- The implementation relied on a mix of reusable editorial primitives and page-local layout recipes.
- Review comments on PR `#71` already identified composition/fidelity issues, but there was no final route-level acceptance matrix across supported viewports.

Corrective action:

- Do one deliberate home QA pass against the reference at canonical desktop widths.
- Remove fragile one-off positioning where it is carrying too much of the composition.

### 5. The app currently mixes two visual systems

Observed now:

- Home and global chrome are editorial.
- Agent workspaces are still bordered, utility-style, and more debug-forward.
- That split makes the product feel unfinished and undermines the value of the new design system.

Root cause:

- Theme and launcher work landed before the shared agent workspace shell.
- There was no hard rule preventing home-only design progress from being read as app-wide redesign progress.

Corrective action:

- Treat the shared agent shell as the next non-optional baseline task.
- Do not claim route-family parity until home, floor-plan, image-analysis, search, and consultation chat all read as one system.

## What went wrong in the process

### 1. Scope blur between PR #70 and the later design expectation

PR `#70` was explicit: it was a quick-fix and polish pass, not a redesign. If later expectations treated it as part of a design-system migration, that was a planning/expectation mismatch rather than a coding mistake.

### 2. PR #71 mixed planning, implementation, and follow-up fixes into one narrative

PR `#71` bundled:

- reference import
- architecture mapping
- theme foundation
- home / launcher implementation
- first review-fix epic
- second review-fix epic

That made it harder to see what was still missing. The landed implementation was only the first visual slice, but the PR told a larger story.

### 3. The plan was phased, but the acceptance model was not explicit enough

The mapping plan was actually directionally correct. It explicitly recommended:

1. theme foundation
2. home and launcher
3. shared shell and context rail
4. search workspace
5. floor-plan workspace
6. consultation rail and regression coverage

The problem was that this phased rollout did not get turned into a page-by-page acceptance contract that stayed visible after merge.

### 4. Review attention centered on the home slice

The PR `#71` comments focused on:

- token fidelity
- the no-line rule
- home composition
- launcher cards
- consultation styling on the home page

That improved the home slice, but it left the live agent workspaces unaudited against the floor-screen reference.

### 5. The epic description and the merged slice were too far apart

Epic `tal_maria_ikea-mi5` defines success as app-wide redesign parity, including agent pages adopting the new shell composition. But the merged implementation slice only touched theme/home/navigation surfaces.

The epic itself remained open, which is correct. The problem was that the PR and follow-up review loop did not keep the remaining route gaps prominent enough.

### 6. `ui/AGENTS.md` was directionally correct but incomplete for rollout control

The local UI guidance correctly says:

- Stitch is the source of truth
- preserve typed React, CopilotKit, and AG-UI seams
- avoid heavyweight redesign rewrites

What it does not currently encode is a route-level completion rule such as:

- do not call the redesign successful until home, search, floor-plan, image-analysis, and the consultation rail all pass reference review
- shared shell migration is required before claiming route-family consistency
- every redesign slice must name the exact pages it does and does not cover

## Did the instructions mismatch?

Partially.

- The PR `#70` instructions matched the code that shipped.
- The Stitch mapping plan also matched a sensible phased rollout.
- The mismatch was between the broader redesign intent and the operational instructions used to evaluate progress.

In practice:

- the plan said the shared shell and workspace redesigns were later slices
- the live screenshots now show that those later slices never happened before merge
- nothing in the local UI guidance forced a hard stop or explicit warning when only the home slice was redesigned

So the issue was not that the agents were told to do the wrong thing. It was that the instructions were not strict enough about what could and could not be considered "done" at each phase.

## Corrective actions

### Product corrective actions

1. Rebuild the shared agent shell around the Stitch composition before doing more local route polish.
2. Restyle the consultation rail and composer as a first-class design surface, not just a CopilotKit skin.
3. Bring search onto the same editorial shell and result hierarchy as the other workspaces.
4. Bring floor-plan intake onto the intended drafting/workbench layout.
5. Bring image-analysis onto the same baseline shell and hierarchy as floor-plan and search.
6. Run one final home composition pass against the reference after the shared shell is in place.

### Process corrective actions

1. Add a route matrix to `ui/AGENTS.md` naming the required surfaces for redesign parity:
   - home
   - navigation
   - search
   - floor-plan
   - image-analysis
   - consultation chat
2. Require every redesign PR to state explicitly:
   - which routes are covered
   - which routes are intentionally deferred
   - which reference artifacts were checked
3. Keep one Beads task per route family instead of treating the redesign as one broad styling stream.
4. Add visual acceptance steps for real routes, not only component-level or home-only review.
5. Avoid PRs that mix planning import, implementation, and multiple rounds of follow-up fidelity fixes unless the remaining gaps are called out explicitly in the final summary.

## Recommended next Beads shape

The follow-up work should be tracked as a corrective epic that references this report and splits into:

1. rollout guardrails and route-level acceptance criteria
2. shared agent shell redesign
3. search workspace parity
4. consultation rail redesign
5. floor-plan workspace parity
6. image-analysis workspace parity
7. home cleanup and final visual alignment
8. route-level regression and visual verification
