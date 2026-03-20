# Agent Workbench Mode Verification

Date: 2026-03-20

## Scope

- `/agents/search`
- `/agents/floor_plan_intake`
- `/agents/image_analysis`
- consultation rail and search result rendering on agent routes

## Reference artifacts

- `spec/uxuimarch20/feedback.md`
- `spec/uxuimarch20/headerspace.png`
- `spec/uxuimarch20/bundledisplay.png`
- `spec/uxuimarch20/searchcard.png`
- `design_references/stitch_design/`

## What was checked

- Shared shell header density on active-thread routes:
  - route title remains visible
  - thread selector and new-thread action stay in the top workbench bar
  - route description drops out once a thread is active
  - thread data is demoted behind a closed disclosure
- Search workspace hierarchy:
  - stage chrome is reduced to a compact strip
  - bundle results appear immediately after the compact stage bar
  - successful validation badges are hidden by default
  - expanded bundle details move directly into item rows without an extra `Included items` block
- Consultation rail density:
  - rail intro header is compact
  - transcript and composer spacing stay bounded
  - search result summaries render as compact transcript artifacts instead of full feature cards
- Floor-plan and image-analysis workbenches:
  - route-specific center panels use compact metadata bars instead of editorial hero headers
  - empty states keep the primary artifact area visible in the first screenful sooner

## States covered locally

- Fresh-thread route state:
  - app-page test covers no-thread search route behavior
  - Playwright real-backend smoke covers creating a new thread on search, floor-plan, and image-analysis routes
- Existing-thread route state:
  - app-page test covers active-thread search chrome
  - Playwright mock route check covers seeded search bundle state
- Success state:
  - component and route checks confirm pass-state validations stay hidden while bundle content remains visible
- Long-content state:
  - Playwright real-backend check confirms the search chat rail stays bounded when long transcript content is injected
- Error and fallback state:
  - app-page test covers warning rendering
  - app-page test covers unknown-agent fallback

## Automated checks run

- `make tidy`
- `cd ui && pnpm test -- src/app/agents/[agent]/page.test.tsx src/components/search/SearchBundlePanel.test.tsx src/components/tooling/ProductResultsToolRenderer.test.tsx src/components/copilotkit/AgentChatSidebar.test.tsx src/components/tooling/FloorPlanPreviewPanel.test.tsx src/components/tooling/ImageAnalysisWorkspacePanel.test.tsx`
- `cd ui && pnpm playwright test e2e/mock-chat.spec.ts`

## What remains deferred

- `make ui-test-e2e-real-ui-smoke` remains the deferred live-route smoke path used in CI after `PR CI` and `Dependency Review` succeed for the PR SHA.
- Full human visual comparison still happens in PR review against the named March 20 feedback screenshots and the Stitch references above.
