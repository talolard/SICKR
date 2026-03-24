# Deployment Project Guiding Principles

This document captures the standing decision rules for the deployment project.
It should be read alongside the canonical deployment spec and its subspecs, and
it should shape future epics, tasks, implementation reviews, and PR summaries.

Canonical deployment spec:
- [final_deployment_recommendation_2026-03-24_synthesized.md](./final_deployment_recommendation_2026-03-24_synthesized.md)

Shared subspec context:
- [subspecs/00_context.md](./subspecs/00_context.md)

Branching rule:
- start all deployment-project implementation from `tal/deployproject` or from
  a stacked branch that descends from it
- treat `tal/deployproject` as the base branch for this deployment effort

## Purpose

The goal of this document is to keep the project from drifting into a
needlessly complex or operations-heavy shape.
When a future task presents multiple valid approaches, these principles should
be used to choose the simpler and more repeatable one.

## 1. Bias For Simplicity And Automation

This is a side project run by one person.
We should bias strongly toward:

- simple systems
- repeatable automation
- easy-to-debug failure modes
- low operator burden

We should bias away from:

- hand-maintained procedures
- operational heroics
- infrastructure that requires frequent manual intervention
- designs that assume regular SSH-based debugging on hosts as the normal first
  step

Desired outcome:
- once deployed, the system should work consistently
- when it fails, the failure should be diagnosable through normal tooling and
  logs, not by needing ad hoc machine access as the first response

Operational note:
- SSH access is allowed as a fallback debugging or recovery tool
- it should not be the default or first-line operational path

## 2. Optimize For Very Low Scale And Low Cost

Expected scale is intentionally small unless later specs say otherwise.

Default planning assumptions:

- one or two concurrent users at most
- activity is infrequent
- low-duty-cycle usage is the norm
- there is no revenue pressure justifying steady-state spend for unused capacity

This means:

- do not optimize early for throughput or large-team operations
- prefer consistent low-ops systems over highly scalable ones
- prefer scale-to-zero or low-idle-cost designs where they do not compromise
  correctness

Example implication:
- Aurora pause-to-zero is desirable because it matches the expected usage model

## 3. Validation Must Be Explicit

Every task should define how it is validated.

Required posture:

- tasks should specify local validation where feasible
- implementation work should describe what was validated
- PR descriptions should say:
  - what was validated
  - how the validation relates to the task
  - how the validation relates to the overall goal
  - what the final status is

The point is not maximal ceremony.
The point is that future readers should be able to see why a change is believed
to work.

Validation rule:

- do not add artificial, ceremonial, or low-signal validation steps just to
  satisfy a process requirement
- use local validation when it is genuinely useful
- if local validation would be artificial, validate in the environment where the
  behavior is real and explain why

## 4. Ignore Backward Compatibility Unless Explicitly Required

There are no real users yet.
That means we should not preserve old patterns, APIs, or library choices just
because they already exist.

Default rule:

- if a better design requires changing a coding pattern, replacing a library, or
  deleting an obsolete layer, do it

Do not add shims or compatibility layers by default.
Only preserve backward compatibility when a task or spec explicitly requires it.

For this deployment project:

- freely replace existing patterns, libraries, or implementation choices when it
  makes the work simpler and the resulting system easier to operate

## 5. Review For Simplicity

Every implementation should ask:

- can this be done with a small well-supported external library instead of
  custom code
- can code be deleted instead of extended
- can a more standard tool or pattern replace a bespoke one
- can the result be made smaller while keeping it clear

This is not an excuse to add dependencies casually.
It is a bias toward simpler and more maintainable systems.

Default preference:

- prefer well-supported off-the-shelf tools over bespoke implementation
- accept adding dependencies when they materially reduce custom code or
  operational burden
- only choose custom implementation when there is a clear reason not to use the
  standard tool

## How To Use These Principles

When writing or reviewing specs, epics, tasks, or PRs:

- cite these principles when they change the recommended approach
- prefer the option that reduces long-term operator burden
- prefer the option that keeps validation explicit
- prefer deleting complexity over preserving it for theoretical future
  compatibility

If a proposed task conflicts with these principles, that conflict should be
spelled out rather than ignored.
