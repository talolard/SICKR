## Summary

Implement the March 18 floor-plan fixes in one coordinated stream, biased toward
reusing existing shared page/chat/attachment/thread/eval infrastructure instead of
adding floor-plan-only plumbing.

## Reuse-first decisions

- Keep CopilotKit + AG-UI as the only chat transport.
- Fix the floor-plan chat layout by replacing the sidebar-style wrapper with an
  in-flow chat pane inside the existing shared agent page shell.
- Reuse the existing attachment flow (`AgentImageAttachmentPanel`,
  `AttachmentComposer`, `/api/attachments`) and widen it to `floor_plan_intake`
  through the existing `agent.setState(...)` path.
- Reuse the existing thread/session bootstrap and transcript snapshot helpers in
  `CopilotKitProviders` and `threadStore` to restore history on refresh.
- Fix asset naming at the thread-data API boundary so the UI receives a readable
  display label instead of inferring one from internal keys or filenames.
- Reuse the existing trace-save bundle flow and the `evals/search` architecture
  for floor-plan eval capture and initial case authoring.

## Implementation slices

1. Shared UI/state:
   - replace `AgentChatSidebar` with an in-flow chat pane primitive
   - render uploads for `floor_plan_intake`
   - persist and restore transcript snapshots on the real agent page
2. Asset metadata:
   - add server-derived display labels for floor-plan assets
   - render the label in `ThreadDataPanel`
3. Evals:
   - add floor-plan eval package scaffold based on `evals/search`
   - capture trace/prompt context artifacts from live floor-plan runs
   - seed the first cases from:
     - `019d01cf54467b5db80da0685a45c7da` for brief opening behavior
     - `019d01d1da6dcb6d07cd57e8cc8c234f` for an invalid render call missing `scene_level`
     - `019d01d3d55c952fd91297f6bf307690` for the corrected render retry
   - add initial terse-first-message cases, even if they fail

## Validation

- Targeted Vitest for chat pane, thread store, attachment panel, and thread data UI
- Targeted pytest for thread-data asset labels and floor-plan eval scaffolding
- `make tidy`
- `make ui-test-e2e-real-ui-smoke` if the runtime/UI path remains practical in the slot
