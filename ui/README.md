# CopilotKit UI Workspace

Next.js App Router workspace for the TypeScript CopilotKit frontend.

## Prerequisites

- Node.js 20 LTS
- `corepack` enabled
- `pnpm` available (this repo uses `pnpm`)

## Commands

```bash
pnpm dev
pnpm dev:mock
pnpm lint
pnpm typecheck
```

## Styling baseline

- Keep `@copilotkit/react-ui/styles.css` as the baseline once CopilotKit UI components are added.
- Use lightweight app-level styling for custom containers and renderers (Tailwind is initialized in this workspace).
