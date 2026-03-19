# March 19 UX/UI Feedback

This document is a first-pass cleanup of the original notes. It is for information gathering, problem framing, and pointing at likely code surfaces. It is not yet an implementation plan.

Note:

- The screenshot files referenced below are available next to this document in the parent working directory.
- They are intentionally not included in this setup commit for the dedicated worktree branch.

## Current UI stack

- `ui/` is a Next.js 16 / React 19 app.
- Chat UI is currently powered by CopilotKit: `@copilotkit/react-core`, `@copilotkit/react-ui`, and `@copilotkit/runtime` at `1.54.0`.
- Styling outside CopilotKit is mostly raw Tailwind CSS v4 utility classes plus a very small global stylesheet in `ui/src/app/globals.css`.
- We are not currently using a shared component library outside CopilotKit. I did not find `shadcn/ui`, Radix, Headless UI, MUI, Chakra, Mantine, or similar packages in the UI workspace.
- Typography is not fully wired up: `ui/src/app/layout.tsx` loads Geist fonts, but `ui/src/app/globals.css` still sets `body` to `Arial, Helvetica, sans-serif`.
- CopilotKit itself is restyled with a custom `style jsx global` block in `ui/src/components/copilotkit/AgentChatSidebar.tsx`.
- Most of the app chrome is custom and repeated: plain `button`, `select`, `details`, `section`, and `div` elements with one-off Tailwind class strings.

## Confirmed issues from screenshots

### 1. Search chat should probably return to a toggleable overlay or sidebar surface

- Screenshots:
  - `./screenshots/chat_breaks_vertical.png`
  - `./screenshots/chat_search_results_too_long.png`
- The current inline chat surface appears worse than the older toggleable or overlay-style chat. The older behavior seems to be gone, not merely hidden.
- Relevant code:
  - `ui/src/components/copilotkit/AgentChatSidebar.tsx`
  - `ui/src/app/agents/[agent]/page.tsx`
  - `ui/src/app/agents/[agent]/agentPageShell.tsx`
- Corroboration from code:
  - I could not find an existing popup, overlay, drawer, or toggleable CopilotKit chat wrapper in `ui/src`.
  - The app currently renders `CopilotChat` inline via `AgentChatSidebar`.

### 2. Chat transcript height and scroll ownership are wrong in the search layout

- Screenshots:
  - `./screenshots/chat_breaks_vertical.png`
  - `./screenshots/chat_search_results_too_long.png`
- Expected behavior:
  - The chat pane should stay within a bounded height.
  - The transcript should own its own scrolling.
  - Long search results should stay inside the chat pane instead of stretching the whole page.
- Relevant code:
  - `ui/src/app/agents/[agent]/agentPageShell.tsx`
  - `ui/src/components/copilotkit/AgentChatSidebar.tsx`
  - `ui/src/components/copilotkit/renderers/shared.tsx`
  - `ui/src/components/tooling/ProductResultsToolRenderer.tsx`
  - `ui/src/components/copilotkit/renderers/useCatalogToolRenderers.tsx`
- Working hypothesis:
  - The search-specific branch in `agentPageShell.tsx` does not establish one clear, bounded scroll container for the right-hand tool-and-chat column.
  - The non-search layout wraps the chat area in `min-h-0`, but the search layout does not do the equivalent.
  - `ProductResultsToolRenderer.tsx` already uses `max-h-96 overflow-y-auto` for each result group, so the renderer is trying to constrain overflow. The bigger problem appears to be the layout above it.

### 3. Bundle hierarchy and collapse affordances are too weak

- Screenshot:
  - `./screenshots/visual_hierarchy_of_bundles.png`
- Problems shown in the screenshot:
  - It is hard to see where one bundle starts and another ends.
  - It is not obvious that each bundle is collapsible.
  - The "Show details" / "Hide details" affordance is too subtle.
  - Several nested areas scroll, but the UI does very little to signal that.
  - Bundle headers, details, and item cards all sit on very similar gray-white surfaces, so the visual hierarchy is weak.
- Relevant code:
  - `ui/src/components/search/SearchBundlePanel.tsx`
  - `ui/src/components/search/BundleProposalSummaryCard.tsx`

### 4. Clicking "New thread" freezes the app or appears to do nothing

- Screenshot:
  - `./page_unresponsive.png`
- Relevant code:
  - `ui/src/app/agents/[agent]/agentPageShell.tsx`
  - `ui/src/app/CopilotKitProviders.tsx`
  - `ui/src/app/agents/[agent]/agentPageHooks.ts`
- Working hypothesis:
  - `createThread()` changes the `threadId` prop passed to `<CopilotKit ... />`, but the CopilotKit provider is keyed only by `agentKey`, not by `threadId`.
  - At the same time, `useThreadSnapshotSync()` immediately swaps message state for the new thread.
  - If CopilotKit does not fully tolerate live thread swaps plus immediate message replacement, that combination is the strongest candidate for the freeze.
- Test gap:
  - There is coverage for thread changes in the debug harness, but not enough real-page end-to-end coverage for `/agents/[agent]`.

### 5. The base UI looks bare and too developer-oriented

- Screenshots:
  - `./screenshots/empty_ugly/search.png`
  - `./screenshots/empty_ugly/floor_plan_intake.png`
  - `./screenshots/empty_ugly/choose_agent.png`
  - `./screenshots/empty_ugly/below_known_facts_should_be_dev_only.png`
- Problems shown in the screenshots:
  - The layout feels like a prototype rather than a product.
  - Large blank regions dominate the page.
  - Visual hierarchy is weak across headings, panels, controls, and empty states.
  - The left-hand inspector panel shows prompt and runtime information that likely belongs behind a debug affordance, not in the default user experience.
- Relevant code:
  - `ui/src/components/agents/AgentInspectorPanel.tsx`
  - `ui/src/components/navigation/AppNavBanner.tsx`
  - `ui/src/app/page.tsx`
  - `ui/src/app/agents/[agent]/agentPageShell.tsx`
- Additional note:
  - `AgentInspectorPanel.tsx` currently renders "Known facts", prompt text, and runtime notes directly in the main layout for all users.

### 6. The "My agents" selector likely needs a better control

- Screenshot:
  - `./screenshots/myagents_selector_doesnt_work.png`
- Relevant code:
  - `ui/src/components/navigation/AppNavBanner.tsx`
- What looks wrong:
  - It is a plain native `<select>`.
  - It loads asynchronously, but there is no loading state or disabled state while options are missing.
  - It is easy to miss visually.
  - On macOS, the native menu is visually detached from the rest of the app and does not feel integrated.

## Additional obvious issues worth tracking

- `ui/src/app/layout.tsx` still has default Create Next App metadata:
  - `title: "Create Next App"`
  - `description: "Generated by create next app"`
- The home page and agent pages reuse a lot of generic border-and-text patterns without a real visual system.
- Empty and loading states are mostly plain text rather than skeletons, placeholders, or stronger guidance.
- The current three-pane search layout is very space-inefficient on large screens while still feeling cramped in the chat column.

## Where these issues show up in code

- Chat surface and chat sizing:
  - `ui/src/components/copilotkit/AgentChatSidebar.tsx`
  - `ui/src/app/agents/[agent]/agentPageShell.tsx`
- Thread switching and likely "New thread" freeze path:
  - `ui/src/app/CopilotKitProviders.tsx`
  - `ui/src/app/agents/[agent]/agentPageHooks.ts`
- Search bundle hierarchy and scroll behavior:
  - `ui/src/components/search/SearchBundlePanel.tsx`
  - `ui/src/components/search/BundleProposalSummaryCard.tsx`
- Product search result rendering inside chat:
  - `ui/src/components/tooling/ProductResultsToolRenderer.tsx`
  - `ui/src/components/copilotkit/renderers/useCatalogToolRenderers.tsx`
- Top-level navigation and agent selector:
  - `ui/src/components/navigation/AppNavBanner.tsx`
- Inspector and developer-facing side content:
  - `ui/src/components/agents/AgentInspectorPanel.tsx`

## Off-the-shelf components and docs to prefer

The main goal should be to stop reinventing basic UI chrome and interaction patterns. We should keep custom code for IKEA-specific renderers, not for generic chat shells, drawers, selects, cards, and collapsible panels.

### CopilotKit components we should seriously consider

From CopilotKit's React UI docs and setup docs, the main chat surface options are:

- `CopilotChat`: inline chat
- `CopilotPopup`: floating trigger + popup chat
- `CopilotSidebar`: toggleable sidebar chat
- `CopilotPanel`: inline panel

Why this matters here:

- If we want to restore the previous "toggleable chat" feel, `CopilotSidebar` is the most obvious off-the-shelf option.
- If we want chat available without permanently consuming page width, `CopilotPopup` is also worth evaluating.
- CopilotKit also documents a "bring your own components" pattern for customizing the window around `CopilotSidebar`, which is promising if we want overlay behavior without rebuilding the chat internals.

Useful references:

- CopilotKit React setup docs:
  - `copilotkit/dev-docs/architecture/setup-react.md`
- CopilotKit custom look and feel / "bring your own components":
  - `copilotkit/docs/snippets/shared/guides/custom-look-and-feel/bring-your-own-components.mdx`

### Off-the-shelf app components that would reduce custom UI code

`shadcn/ui` looks like the best fit if we want better UI without adopting a heavy framework. It matches our current Tailwind-based setup and gives us accessible building blocks for common patterns.

Components that seem especially relevant:

- `ScrollArea`
  - Good for making scroll ownership explicit in chat transcripts, bundle lists, long notes, and inspector content.
- `Accordion` or `Collapsible`
  - Better bundle expand/collapse behavior with clear triggers and state cues.
- `Card`
  - A better baseline for panels than repeating slightly different border-and-background utility strings everywhere.
- `Sheet`
  - A strong candidate for movable or temporary side panels, especially on smaller screens.
- `Sidebar`
  - Useful if we want a more deliberate left-nav or inspector pattern instead of the current always-open box.
- `Select`
  - Better than the current native agent selector if we want a styled but still simple replacement.
- `Command` / combobox pattern
  - Likely a better agent picker than `Select` if the list grows and we want search.
- `Tabs`
  - A good way to separate customer-facing context from prompt/debug/runtime details.
- `Badge`
  - Cheap visual hierarchy for validations, counts, states, and labels.
- `Separator`
  - Helps establish structure inside dense bundle cards and inspector panels.
- `Tooltip`
  - Useful for terse controls like collapse buttons, info icons, and technical metadata.
- `Skeleton`
  - Better loading states for agent lists, thread metadata, and bundle panels.
- `Resizable`
  - Worth considering if we keep a multi-pane desktop workbench instead of moving chat into a toggleable surface.

Useful references:

- shadcn/ui docs home:
  - `https://ui.shadcn.com`
- Likely relevant component docs:
  - `https://ui.shadcn.com/docs/components/accordion`
  - `https://ui.shadcn.com/docs/components/collapsible`
  - `https://ui.shadcn.com/docs/components/card`
  - `https://ui.shadcn.com/docs/components/scroll-area`
  - `https://ui.shadcn.com/docs/components/select`
  - `https://ui.shadcn.com/docs/components/sheet`
  - `https://ui.shadcn.com/docs/components/sidebar`
  - `https://ui.shadcn.com/docs/components/tabs`
  - `https://ui.shadcn.com/docs/components/tooltip`
  - `https://ui.shadcn.com/docs/components/skeleton`

## Suggested direction for the next iteration

This is the smallest-complexity direction that currently looks sensible:

1. Let CopilotKit own more of the chat shell again, probably via `CopilotSidebar` or `CopilotPopup`, instead of continuing to fight the inline three-pane search layout.
2. Add a small off-the-shelf component layer for the rest of the app chrome, most likely `shadcn/ui`.
3. Move prompt and runtime notes behind a debug affordance or secondary tab instead of showing them in the default user-facing layout.
4. Tighten the visual system before adding more bespoke widgets: typography, spacing, panel hierarchy, loading states, and scroll behavior should become consistent first.
