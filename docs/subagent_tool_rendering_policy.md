# Agent Tool Rendering Policy

This policy keeps tool UX consistent across first-class agents in the CopilotKit UI.

## Required contract for user-visible tools

1. Backend tool contract is typed and stable.
2. Copilot chat renderer exists for the tool in `ui/src/components/copilotkit/CopilotToolRenderers.tsx`.
3. If a tool needs persistent page-level visualization, add a dedicated panel component.

## Agent behavior

- Agent pages reuse the same CopilotKit tool renderers.
- If a tool has a page-level panel, reuse it across agents when relevant.
- If no page-level panel is needed, chat rendering alone is enough.

## Avoid

- Adding a backend tool that emits user-facing results with no renderer.
- Creating agent-specific JSON formats when a shared format already exists.
