# March 19 Designer Review Brief

This document is intended for design review. It summarizes the current UX and visual problems in the IKEA agent UI, shows which screenshots demonstrate them, and frames the questions we want a designer to help solve.

The goal is not pixel-perfect feedback on the current UI. The goal is to step back and ask what this product should feel like, how people should move through it, and how to make it usable without adding unnecessary implementation complexity.

Note:

- The screenshot files referenced below are available next to this document in the parent working directory.
- They are intentionally not included in this setup commit for the dedicated worktree branch.

## What This Product Is

This UI is a workspace for IKEA-focused AI agents. Today there are multiple agents, including:

- a search agent for finding IKEA products and proposing bundles
- a floor-plan intake agent for collecting room context and generating floor-plan outputs
- an image-analysis agent for room-photo analysis

At a high level, the product is trying to help a user move from:

- describing a room or need
- to seeing relevant suggestions, analyses, and proposed product groupings
- to refining those suggestions through chat and structured outputs

So the design problem is not just "make it prettier." It is:

- make the experience feel trustworthy
- make it clear what the system is doing
- make it obvious where to look
- make it easy to switch between conversation and structured results
- keep the interface from feeling like an internal tool

## What We Want From Design

We want design help with both UX and visual direction.

Specifically:

- a clearer overall product structure
- stronger hierarchy between navigation, chat, work output, and supporting information
- better handling of dense results such as bundles and product lists
- better empty states and loading states
- a more intentional visual language
- a recommendation for what should be always visible versus tucked away
- solutions that ideally use off-the-shelf patterns and components rather than bespoke UI inventions

We are open to a broader redesign than the "smallest complexity" path if that produces a much better outcome. That said, we still want designs that are realistic to build in a product that already uses CopilotKit for chat and Tailwind for the rest of the app.

## Product-Level Design Goals

At the design level, we think the UI should achieve the following:

- The product should feel like a guided design assistant, not a raw engineering console.
- The primary user task should be obvious within a few seconds.
- The chat should support the workflow, not dominate or destabilize the layout.
- Structured outputs such as bundles, product results, and floor-plan previews should feel first-class.
- Dense information should be scannable before it is readable in detail.
- Debug and developer-facing information should not compete with user-facing content.
- The interface should feel calm, modern, and intentional, even when a lot of information is on screen.

## Screenshots To Review

- `./screenshots/chat_breaks_vertical.png`
- `./screenshots/chat_search_results_too_long.png`
- `./screenshots/visual_hierarchy_of_bundles.png`
- `./page_unresponsive.png`
- `./screenshots/myagents_selector_doesnt_work.png`
- `./screenshots/empty_ugly/search.png`
- `./screenshots/empty_ugly/floor_plan_intake.png`
- `./screenshots/empty_ugly/choose_agent.png`
- `./screenshots/empty_ugly/below_known_facts_should_be_dev_only.png`

## Major UX And Visual Problems

### 1. The interface has no clear primary focus

Relevant screenshots:

- `./screenshots/empty_ugly/search.png`
- `./screenshots/empty_ugly/floor_plan_intake.png`

What seems wrong:

- It is not immediately obvious what the most important region of the page is.
- The page is split into multiple bordered boxes of roughly similar visual weight.
- The chat, workbench, and side information compete with each other.
- Large empty regions make the page feel unfinished rather than spacious.

Why this matters:

- A user should be able to understand the page structure instantly.
- Right now the layout asks the user to decode the product before they can use it.

What we want design help with:

- What should be the primary focal area on each agent page?
- Should chat be persistent, tucked away, toggleable, or context-dependent?
- How should a search workflow differ visually from a floor-plan workflow?
- What information is essential at all times versus secondary?

### 2. The current UI feels like a prototype, not a product

Relevant screenshots:

- `./screenshots/empty_ugly/search.png`
- `./screenshots/empty_ugly/floor_plan_intake.png`
- `./screenshots/empty_ugly/choose_agent.png`

What seems wrong:

- Most surfaces are plain white or light gray boxes with thin borders.
- Typography is generic and not doing much work.
- There is little visual rhythm, emphasis, or personality.
- Empty states are especially bare.
- Controls and surfaces feel ungrouped and underdesigned.

Why this matters:

- Users will read visual roughness as product uncertainty.
- The product needs to feel reliable and considered if it is going to make suggestions about a room, products, or design decisions.

What we want design help with:

- What should the visual language be?
- How should the UI feel: domestic, editorial, utilitarian, high-trust retail assistant, something else?
- How much visual richness is appropriate without getting in the way of dense results?
- What are the minimum changes that would make this feel substantially more intentional?

### 3. Chat is destabilizing the page instead of supporting it

Relevant screenshots:

- `./screenshots/chat_breaks_vertical.png`
- `./screenshots/chat_search_results_too_long.png`

What seems wrong:

- As the conversation grows, the chat region appears to grow with it.
- Search results inside the chat are visually and spatially overwhelming.
- The page feels like it is losing containment as more content arrives.
- It becomes unclear what should scroll: the page, the chat, or the individual result cards.

Why this matters:

- Chat is meant to be the control surface for the workflow.
- It should not break the layout or turn the rest of the interface into a secondary afterthought.

What we want design help with:

- Should chat live inline, in a sidebar, as a popup, or in an overlay?
- How should long structured content appear inside or adjacent to chat?
- What is the right balance between conversational flow and structured work surfaces?
- When should a generated result stay inside the transcript versus get promoted into the main work area?

### 4. Result-heavy content is difficult to scan

Relevant screenshots:

- `./screenshots/chat_search_results_too_long.png`
- `./screenshots/visual_hierarchy_of_bundles.png`

What seems wrong:

- Cards are dense but not strongly organized.
- Item metadata, titles, descriptions, and prices compete for attention.
- Repetition of similar card patterns makes it harder to distinguish summary from detail.
- Scrollable areas are not clearly signaled.

Why this matters:

- Product search and bundle review are central tasks.
- Users need to be able to skim many options quickly, then drill into one.

What we want design help with:

- How should product results be summarized for fast scanning?
- How should bundle summaries differ from bundle details?
- What should be shown by default versus hidden behind expansion?
- How should we signal nested scrolling, truncation, and expandability?

### 5. Bundle hierarchy is too weak

Relevant screenshot:

- `./screenshots/visual_hierarchy_of_bundles.png`

What seems wrong:

- It is hard to tell where one bundle ends and another begins.
- The bundle header does not feel meaningfully separate from the expanded contents.
- The collapse/expand affordance is too subtle.
- The selected or recommended bundle does not stand out strongly enough.

Why this matters:

- Bundles are one of the highest-value outputs of the search workflow.
- If the user cannot scan and compare them quickly, the most useful output of the system feels laborious.

What we want design help with:

- What is the right information architecture for a bundle?
- What should the bundle header contain?
- How should "selected," "recommended," or "best fit" states appear?
- How much detail should be visible before expansion?

### 6. Developer-facing information is too prominent

Relevant screenshot:

- `./screenshots/empty_ugly/below_known_facts_should_be_dev_only.png`

What seems wrong:

- The left rail shows prompt and runtime information that feels internal.
- It is presented with similar weight to actual user-facing content.
- The UI does not distinguish clearly between customer value and debugging context.

Why this matters:

- This makes the product feel like a demo or internal tool.
- It distracts from the actual task.

What we want design help with:

- What should a user-facing left rail contain, if anything?
- Which information should move behind a debug affordance, settings area, or expandable drawer?
- Is there a better way to present "known facts" so it feels useful rather than technical?

### 7. Navigation and switching controls are weak

Relevant screenshots:

- `./screenshots/myagents_selector_doesnt_work.png`
- `./screenshots/empty_ugly/choose_agent.png`

What seems wrong:

- The current agent picker feels like a default browser control rather than part of the product.
- The home or choose-agent page is functional but visually flat.
- There is little sense of what each agent is for, when to use it, or how the options relate to one another.

Why this matters:

- Choosing the right entry point is one of the first decisions in the product.
- If that choice feels unclear or unimportant, the product loses clarity immediately.

What we want design help with:

- What is the best pattern for selecting agents?
- Should agent selection feel like navigation, workspace switching, or choosing a mode?
- How should we explain the differences between agents?
- Should the home page be more of a dashboard, launcher, or guided starting point?

### 8. Empty states do not guide the user

Relevant screenshots:

- `./screenshots/empty_ugly/search.png`
- `./screenshots/empty_ugly/floor_plan_intake.png`
- `./screenshots/empty_ugly/choose_agent.png`

What seems wrong:

- Empty states look like blank containers rather than invitations to act.
- They explain little about what the user should do next.
- They do not create momentum.

Why this matters:

- Empty states are the first-run experience.
- In an AI workflow, they need to reduce uncertainty and help the user begin.

What we want design help with:

- What should empty states say and show?
- Should they include examples, starter prompts, suggested tasks, or visual previews?
- How can we make each agent's zero-state feel specific to that workflow?

### 9. The UI is not communicating system status well

Relevant screenshots:

- `./screenshots/chat_search_results_too_long.png`
- `./page_unresponsive.png`

What seems wrong:

- When things get long, busy, or unresponsive, the system does not clearly communicate what is happening.
- The user can end up in a state where the page feels stalled or overloaded.

Why this matters:

- AI systems need strong state communication because outputs appear incrementally and can be long-running.
- If the user loses confidence in system state, trust drops quickly.

What we want design help with:

- How should the UI communicate loading, generating, saved, syncing, or failed states?
- What should happen visually when a thread is created, switched, or resumed?
- How can we make long-running operations feel stable rather than fragile?

## Design Questions We Would Like Answered

We would like the designer to respond with ideas, critiques, and proposed directions for the following questions:

- What should the overall page architecture be for an AI-assisted shopping and planning workspace?
- Should chat be the main surface, a side surface, or a temporary surface?
- What should the visual hierarchy be between:
  - navigation
  - chat
  - generated work output
  - user-uploaded context
  - debug or internal information
- How should result-heavy outputs such as bundles and product lists be structured for scanability?
- How should we handle dense information without making the interface look heavy?
- What should be visible by default on desktop?
- What should collapse or move on smaller screens?
- What should the entry experience be for a first-time user?
- What design language would make this feel like a coherent product rather than a technical demo?

## What We Think The Design Should Optimize For

If tradeoffs are needed, we currently think the design should prioritize:

1. clarity of workflow
2. readability and scanability
3. stability of layout
4. trust and product polish
5. low cognitive load
6. realistic implementation complexity

## Constraints And Preferences

These are useful to know while proposing solutions:

- We would prefer to use existing components and established UI patterns where possible.
- The product already uses CopilotKit for chat.
- We are open to using more off-the-shelf UI building blocks rather than custom one-off components.
- We do not want to solve every problem with bespoke animation or unusual interaction patterns.
- We are willing to put in real effort on the UI if the design direction is strong.
- We still want the result to be buildable by a small engineering team without turning the front end into a design-system project of its own.

## What A Good Outcome Looks Like

A strong design response would help us answer:

- what this product should feel like
- how the user should move through each workflow
- where chat belongs
- what should be first-class versus secondary
- how to make dense results calm and legible
- how to remove the "internal tool" feel without losing useful functionality

If helpful, we would welcome any of the following from design:

- annotated mockups
- alternative layout directions
- notes on information hierarchy
- recommendations on what to hide, collapse, elevate, or remove
- visual references or component-pattern references
- a "lighter lift" option and a "more ambitious" option
