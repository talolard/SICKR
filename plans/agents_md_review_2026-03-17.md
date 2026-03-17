# AGENTS.md Review Packet (2026-03-17)

## Summary

`AGENTS.md` currently mixes durable repo-wide policy with role behavior, subsystem implementation guidance, and protocol/tutorial detail. The file should be reduced to repo invariants plus short pointers to canonical docs.

This packet is the review artifact for `tal_maria_ikea-1iw.19` and the Tal gate `tal_maria_ikea-1iw.25.2`. It does not apply policy changes yet.

## Sources Reviewed

### Repo-local sources

- `AGENTS.md`
- `docs/codex_multi_agent_workflow.md`
- `docs/worktree_multi_agent_workflow.md`
- `docs/merge_runbook.md`
- `docs/subagent_tool_rendering_policy.md`
- `external_docs/pydantic_ai_ag_ui.md`
- `spec/ui/pydanticai_copilotkit_integration.md`

### Primary/external sources

- OpenAI Codex best practices:
  - `https://developers.openai.com/codex/learn/best-practices/`
- Anthropic Claude Code memory / `CLAUDE.md` guidance:
  - `https://docs.anthropic.com/en/docs/claude-code/memory`
- GitHub Copilot repository custom instructions:
  - `https://docs.github.com/en/copilot/how-tos/custom-instructions/adding-repository-custom-instructions-for-github-copilot`
  - `https://docs.github.com/en/copilot/tutorials/customization-library/prompt-crafting-for-custom-instructions`

## External Guidance Distilled

- Repo instruction files should define what is stable and broadly applicable across work in the repository: where to find context, how to validate, and what conventions must always hold.
- Repeated workflows should move into reusable skills or narrower role-specific prompts instead of staying as long repo-wide prose.
- Repository instructions should stay short, self-contained, and human-readable; deeper architecture, transport, and UI details should live in linked canonical docs/specs.

## Repo-Specific Findings

### Keep in `AGENTS.md`

- Repo-wide workflow invariants:
  - worktree requirement
  - merge queue / merge ownership policy
  - `make tidy` and behavioral readiness gates
  - typing and test expectations
  - git identity
  - Beads as the issue tracker
- Small, durable repo-shape facts:
  - where active runtime, tests, docs, plans, and UI live
  - `legacy/` is reference-only
- Short routing guidance:
  - role prompts live under `.codex/agents/`
  - canonical docs/specs live under `docs/`, `spec/`, and `external_docs/`

### Move out of `AGENTS.md` and replace with pointers

- Detailed Codex role-system explanation:
  - keep one sentence in `AGENTS.md`
  - point to `docs/codex_multi_agent_workflow.md`
- Detailed worktree lifecycle and slot/port isolation:
  - keep the mandatory `make agent-start` rule in `AGENTS.md`
  - point to `docs/worktree_multi_agent_workflow.md`
- CopilotKit / AG-UI protocol detail:
  - move out of repo policy
  - point to `external_docs/pydantic_ai_ag_ui.md` and `spec/ui/pydanticai_copilotkit_integration.md`
- Tool-renderer implementation contract:
  - move out of repo policy
  - point to `docs/subagent_tool_rendering_policy.md` plus the UI spec
- Tool implementation placement details:
  - keep only the stable repo location rule if desired
  - move path-by-path implementation tutorial detail into docs

### Delete or trim from `AGENTS.md`

- Stale repository-structure claims:
  - `comments/` is listed as current repo structure, but the directory is not present in this checkout
- Duplicated workflow detail:
  - worktree and merge guidance appears in both `Agent Fast Paths` and `Worktree + Merge Queue Policy`
- Subsystem-specific doctrine that is not clearly enforced repo-wide:
  - large parts of `Tool Rendering (CopilotKit)`
  - large parts of `UI + AG-UI integration (CopilotKit + PydanticAI)`
- Tutorial-style implementation specifics:
  - step-by-step backend/frontend tool-rendering requirements read more like a runbook/spec than top-level repo policy

## Minimal Approved Cleanup I Recommend

If Tal approves cleanup, the lowest-risk patch is:

1. Keep `AGENTS.md`, but cut it down to:
   - repo layout
   - workflow/worktree policy
   - validation gates
   - typing/testing expectations
   - high-level runtime invariants
   - logging / git identity / Beads policy
2. Replace the long CopilotKit / AG-UI / tool-rendering sections with a short pointer block:
   - `docs/subagent_tool_rendering_policy.md`
   - `external_docs/pydantic_ai_ag_ui.md`
   - `spec/ui/pydanticai_copilotkit_integration.md`
3. Collapse duplicated worktree/merge instructions into one short section that links to:
   - `docs/worktree_multi_agent_workflow.md`
   - `docs/merge_runbook.md`
4. Remove stale repo-structure entries and any section that no longer matches the current tree.

## Tal Decisions Needed Before `.25.3`

- Whether `Chat Runtime Standards` should stay as repo policy or be split into:
  - short repo invariants in `AGENTS.md`
  - implementation guidance in `docs/` or `spec/`
- Whether `Implementing Tools` belongs in `AGENTS.md` at all, or should become a docs pointer only.
- Whether historical/handoff docs should continue to live under `docs/` when they are not current runbooks.

## Proposed Follow-On for `.25.3`

After Tal approval:

1. Edit `AGENTS.md` only where approved.
2. Update any linked docs/specs so they become the explicit source of truth for moved detail.
3. Re-run `make tidy`.
4. Keep the AGENTS cleanup in its own commit so the policy diff is easy to review.
