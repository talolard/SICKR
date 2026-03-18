# Floor Plan Agent Fixes Retrospective

Date: 2026-03-18
Related work: PR `#65`

## Summary

The floor-plan fixes were not one isolated bug. They were a cluster of regressions caused by shared shell behavior drifting away from the floor-plan workflow:

- chat was still using sidebar behavior even when rendered inside the page
- image uploads were only wired for `image_analysis`
- thread identity restored on refresh, but CopilotKit messages did not
- asset metadata exposed internal ids instead of user-facing labels
- there was no floor-plan eval scaffold to pin current behavior

The main lesson is that floor-plan intake should keep using shared infrastructure, but the shared infrastructure needs to be widened deliberately when a second agent depends on it.

## What Broke

### 1. The chat component choice mattered more than the page layout

The visible overlay bug was not primarily a CSS spacing problem. The agent page already had a workable multi-pane layout, but `AgentChatSidebar` still wrapped `CopilotSidebar`, which brought sidebar behavior into a page where we wanted a normal in-flow pane.

Lesson:
- if chat is meant to behave like page content, use an inline chat primitive, not a sidebar primitive styled to look inline

### 2. Shared flows had become single-agent flows

Uploads existed end to end, but the agent page only rendered and forwarded attachments for `image_analysis`. Floor-plan intake lost the feature because the shared path had quietly narrowed to one agent.

Lesson:
- when a shared workflow is agent-capable, gate it by explicit capability checks, not by hard-coding one currently active agent

### 3. Refresh persistence was only half implemented

The app already restored thread ids and had a thread snapshot store, but the visible CopilotKit message list was not being reloaded into the page. That made refresh look like data loss even though most of the persistence plumbing already existed.

Lesson:
- restore the actual rendered chat state, not just the thread key
- if a shared store exists, consume it directly instead of adding a second local cache

### 4. Asset naming belongs at the API boundary

The UI was showing low-level asset names because the backend returned only internal-ish metadata. Trying to prettify those names in React would have been brittle.

Lesson:
- if users need readable labels, add `display_label` or equivalent typed metadata in the backend payload and keep the UI dumb

### 5. Cold-start behavior exposed races that warm local testing hid

The real-UI smoke test could pass when the backend and UI were already warm, but fail from a clean worktree because the wrapper and first-render timing were brittle. The page would sometimes send before hydration had settled, and the smoke wrapper itself had startup path issues.

Lesson:
- keep one repo-standard smoke command that can boot from zero in a clean worktree
- explicitly test cold-start behavior; warm dev servers hide real regressions

## What Worked

### Keep the fixes in shared seams

The strongest pattern in this effort was fixing problems at shared boundaries instead of layering floor-plan-specific one-offs:

- page shell in `ui/src/app/agents/[agent]/page.tsx`
- shared chat wrapper in `ui/src/components/copilotkit/AgentChatSidebar.tsx`
- shared thread snapshot store in `ui/src/lib/threadStore.ts`
- thread data API metadata in `src/ikea_agent/chat_app/thread_api_models.py`
- thread query projection in `src/ikea_agent/persistence/thread_query_repository.py`

This kept the fixes small and made them useful beyond floor-plan intake.

### Start with transport and metadata, not presentation hacks

Once the right data and message state were flowing, the UI fixes were straightforward. The reverse would have produced fragile behavior.

### Reusing the search eval structure was the right move

Floor-plan eval work went faster once it copied the search eval architecture directly:

- typed datasets
- shared evaluators
- captured trace grounding
- code-first cases instead of ad hoc notebooks

That avoided inventing a second eval style for no benefit.

## Patterns To Reuse

- Prefer capability-based shared agent shell logic over agent-name-specific forks.
- Use inline chat primitives for in-page chat and sidebar primitives only for actual sidebars.
- Persist rendered transcript state anywhere refresh behavior matters.
- Put user-facing display labels into typed backend contracts.
- Treat cold-start smoke tests as product checks, not just CI wrappers.
- Build new eval suites by cloning the strongest existing repo pattern and changing only case content.

## Follow-Ups Worth Keeping In Mind

- The floor-plan page is now functionally correct, but `ui/src/app/agents/[agent]/page.tsx` still carries a lot of coordination logic and is a good future refactor target.
- Coverage is still low on the main agent page and some CopilotKit integration surfaces, so future UI work there should arrive with direct tests.
- The remaining product-title enrichment work for catalog items is the same class of problem as asset labels: solve it in metadata, not with frontend string heuristics.

## Short Version

The fastest safe fixes came from widening shared infrastructure, not from building floor-plan-only patches. The main failures were all variants of the same mistake: the product looked shared, but some critical behavior had drifted into one-off or half-connected implementations.
