# OpenAI Codex plan-mode reference notes

Source:
- `https://raw.githubusercontent.com/openai/codex/refs/heads/main/codex-rs/core/templates/collaboration_mode/plan.md`

This file captures the parts of the official plan-mode template that are most relevant to our `spec_planner` behavior.

## Relevant principles

- Planning is most useful when work is non-trivial, multi-phase, ambiguous, or requires checkpoints.
- Plans should use meaningful steps, not filler.
- A plan should make sequencing visible.
- One agent should not pretend work is ready if the understanding is still fuzzy.
- Clarifying questions should be concise and only asked when they materially reduce risk.
- The planner should keep the user informed about what is still unknown and what comes next.

## How to adapt this for our `spec_planner`

For our workflow, the `spec_planner` should combine those plan-mode principles with a stronger specification loop:
- ask whether the goal is actually understood
- identify the decisions that must be made before task writing starts
- summarize the current state of understanding
- test whether we are ready to hand off to `epic_writer`

## Prompt inclusion guidance

The `spec_planner` prompt should reference this file and adopt its planning discipline, but it should remain focused on specification and user collaboration rather than directly writing implementation tasks.
