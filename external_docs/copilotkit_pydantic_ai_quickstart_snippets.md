# CopilotKit + PydanticAI Quickstart (Website Snippets)

This file captures the relevant code snippets from CopilotKit’s PydanticAI quickstart pages so we
can implement against the upstream “source of truth” (and not stale third-party docs).

## Quickstart: Required Wiring

Install deps:

```bash
npm install @copilotkit/react-ui @copilotkit/react-core @copilotkit/runtime @ag-ui/client
```

Next.js runtime route:

```ts
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();
const runtime = new CopilotRuntime({
  agents: {
    my_agent: new HttpAgent({ url: "http://localhost:8000/" }),
  }
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

Root layout provider:

```tsx
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/v2/styles.css";

export default function RootLayout({ children }: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit" agent="my_agent">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

Page mounting a sidebar:

```tsx
import { CopilotSidebar } from "@copilotkit/react-core/v2";

export default function Page() {
  return (
    <main>
      <h1>Your App</h1>
      <CopilotSidebar />
    </main>
  );
}
```

## Tool Rendering (Generative UI)

Named tool renderer:

```tsx
import { useRenderTool } from "@copilotkit/react-core/v2";

const YourMainContent = () => {
  useRenderTool({
    name: "get_weather",
    render: ({ status, args }) => {
      return (
        <p className="text-gray-500 mt-2">
          {status !== "complete" && "Calling weather API..."}
          {status === "complete" && `Called the weather API for ${args.location}.`}
        </p>
      );
    },
  });
};
```

Fallback renderer:

```tsx
import { useDefaultRenderTool } from "@copilotkit/react-core/v2";

const YourMainContent = () => {
  useDefaultRenderTool({
    render: ({ name, args, status, result }) => {
      return (
        <div style={{ color: "black" }}>
          <span>
            {status === "complete" ? "✓" : "⏳"}
            {name}
          </span>
          {status === "complete" && result && (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          )}
        </div>
      );
    },
  });
};
```

## Shared State (PydanticAI <-> CopilotKit)

Backend pattern (PydanticAI state via `StateDeps` + `StateSnapshotEvent`):

```py
from pydantic_ai.ag_ui import StateDeps
from ag_ui.core import StateSnapshotEvent, EventType

agent = Agent("openai:gpt-5.2-mini", deps_type=StateDeps[AgentState])

@agent.tool
async def add_search(ctx: RunContext[StateDeps[AgentState]], new_query: str) -> StateSnapshotEvent:
  # update ctx.deps.state ...
  return StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=agent_state)

app = agent.to_ag_ui(deps=StateDeps(AgentState()))
```

Frontend pattern (`useAgent` reading state):

```tsx
import { useAgent } from "@copilotkit/react-core/v2";

useAgent({
  agentId: "my_agent",
  render: ({ state }) => (
    <div>{state.searches?.map(...)}</div>
  ),
});
```

Frontend writing state (`agent.setState`) and rerunning:

```tsx
import { useAgent, useCopilotKit } from "@copilotkit/react-core/v2";

const { agent } = useAgent({ agentId: "my_agent" });
const { copilotkit } = useCopilotKit();

agent.setState({ language: "spanish" });
agent.addMessage({ id: crypto.randomUUID(), role: "user", content: "language changed" });
await copilotkit.runAgent({ agent });
```

