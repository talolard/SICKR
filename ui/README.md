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
pnpm test
pnpm test:e2e
pnpm test:e2e:real
```

## Runtime routing

- Next.js runtime route: `POST /api/copilotkit`
- Python AG-UI backend URL is read from `PY_AG_UI_URL`.
- Default backend URL: `http://localhost:8000/ag-ui`

## Separate-process workflow

Run backend and UI in separate terminals:

```bash
make chat
make ui-dev-real
```

Run real-backend E2E smoke (with backend already running):

```bash
make ui-test-e2e-real
```

Mock exploration mode:

```bash
make ui-dev-mock
```

## Styling baseline

- Keep `@copilotkit/react-ui/styles.css` as the baseline once CopilotKit UI components are added.
- Use lightweight app-level styling for custom containers and renderers (Tailwind is initialized in this workspace).
