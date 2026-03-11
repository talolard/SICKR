# Epic structure guide

This file is a reusable guide for writing strong epics and task breakdowns.
It should be included or referenced by the `epic_writer` prompt, and it should inform how the `spec_planner` gathers information before decomposition.

## Purpose

A good epic is not just a list of tasks. It is a decision record, a scope boundary, a handoff artifact, and an execution plan.

A strong epic should make it easy for a future reader or worker to answer:
- Why are we doing this?
- What is in scope and out of scope?
- What are the key design decisions?
- Who owns which parts?
- What exact artifacts will exist when the work is done?
- What order should the work happen in?
- What could be ambiguous or conflict later?
- What does “done” mean objectively?

## Recommended structure

### 1. Summary

Start with a short description of the change in plain language.

Why:
- It gives orientation before detail.
- It helps future readers quickly decide whether the epic is relevant.

### 2. Why we need this

Explain the motivation and current pain points.

Why:
- It captures the problem, not just the proposed fix.
- It prevents future readers from undoing decisions they do not understand.

### 3. Goals

List the intended outcomes.

Why:
- This defines what success looks like.
- It gives implementation workers a target to optimize for.

### 4. Non-goals

Explicitly state what this work does not attempt to do.

Why:
- This prevents scope creep.
- It makes tradeoffs visible and intentional.

### 5. Core design decisions

Call out the architectural decisions and their rationale.

Why:
- Important choices should not be buried across tasks.
- This creates one place where future readers can understand “why it was built this way”.

### 6. Role / component breakdown

When the work involves multiple roles, subsystems, or components, describe each using a consistent pattern:
- Name / role
- Responsibilities
- Why it exists

Why:
- Structured repetition improves readability.
- It makes boundaries and responsibilities explicit.

### 7. Ownership model

State clearly who is accountable for what.

Why:
- Many workflow failures come from fuzzy ownership, not missing implementation.
- Ownership should be explicit for implementation, readiness, review, and merge.

### 8. Conflict analysis and resolutions

List likely ambiguities, tensions, or edge cases, and resolve them explicitly.

Why:
- A good epic anticipates confusion before it happens.
- This reduces implementation churn and inconsistent decisions later.

### 9. Deliverables

List the exact files, configs, prompts, scripts, docs, or artifacts the epic should produce.

Why:
- It makes the output concrete.
- It lets the reviewer compare the result against the expected artifact list.

### 10. Sequencing / phases

Group the work into logical phases.

Why:
- Good phases reduce thrash.
- They help workers understand dependencies and safe ordering.

### 11. Acceptance criteria

Define an objective done state.

Why:
- Acceptance criteria create a shared finish line.
- They help reviewers and future agents decide whether the epic is complete.

### 12. Explicit review gate

When the work changes workflow, prompts, or agent behavior, add a human review checkpoint before rollout.

Why:
- Some work should not go straight from draft to default behavior.
- A review gate is especially important for prompts, policies, and workflow automation.

## Good structural patterns to reuse

These patterns from the current multi-agent epic should be reused intentionally:
- Clear framing up front: Summary, then Why we need this.
- Goals vs Non-goals: sharply defines scope.
- Explicit design decisions section: captures architecture and rationale.
- Role / component breakdown with a repeated structure.
- Ownership model section: clearly states accountability.
- Conflict analysis: anticipates ambiguity and resolves it explicitly.
- Separation of policy vs implementation: explains where instructions live and why.
- Concrete deliverables list: specifies the exact artifacts to produce.
- Phased sequencing: groups work into logical phases.
- Acceptance criteria: defines an objective done state.
- Explicit review gate: inserts a human checkpoint before rollout.

## Good verbosity patterns to reuse

The right kind of verbosity improves comprehension.

Reuse these patterns:
- Explain the “why,” not just the “what”.
- Repeat critical boundaries in more than one section when that reduces ambiguity.
- Use concrete examples and file paths instead of abstractions.
- Prefer short structured blocks over long dense paragraphs.
- Call out edge cases and likely conflicts directly.
- Include operational detail where needed so the epic can actually be executed.

## Rule of thumb for epic quality

A good epic should be executable by another agent without needing the original author present.
If the epic would leave a future worker asking “what exactly do you want?” or “why was this decision made?”, it is not detailed enough yet.
