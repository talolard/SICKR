# CopilotKit Performance Research Notes (2026-03-20)

This note captures the current evidence behind the local UI slowdown investigation so we do not have to re-derive it the next time the question comes up.

## TL;DR

- The current evidence points more strongly at CopilotKit than at Next.js.
- Next.js is still doing useful work in this repo, but mostly as an integrated frontend server and proxy layer, not as the main reason the UI exists in its current shape.
- Moving to plain React or Vite may improve the local dev loop, but it will not be a free win if we keep the same heavy CopilotKit UI surface, and it will require replacing the current `ui/src/app/api/**` responsibilities somewhere else.

## Repo-specific observations

- All four page entrypoints are client components:
  - `ui/src/app/page.tsx`
  - `ui/src/app/agents/page.tsx`
  - `ui/src/app/agents/[agent]/page.tsx`
  - `ui/src/app/debug/agui-harness/page.tsx`
- The current app is using Next.js for more than routing:
  - `ui/src/app/CopilotKitProviders.tsx` points CopilotKit at the same-origin runtime URL `/api/copilotkit`.
  - `ui/src/app/api/copilotkit/handler.ts` hosts the CopilotKit runtime endpoint and builds the AG-UI agent map.
  - `ui/src/app/api/agents/route.ts`, `ui/src/app/api/thread-data/[...segments]/route.ts`, `ui/src/app/api/attachments/route.ts`, and `ui/src/app/attachments/[attachment_id]/route.ts` proxy backend functionality through the Next app.
  - `ui/next.config.ts` uses a Next rewrite for dev product-image proxying.
- The main agent chat surface still renders `CopilotChat` from `@copilotkit/react-ui` in `ui/src/components/copilotkit/AgentChatSidebar.tsx`.

## Local measurements and findings

The local investigation on issue `tal_maria_ikea-19y` produced these results:

- Cold-loading `/agents/search` in Next dev with `NEXT_PUBLIC_USE_MOCK_AGENT=1` still took roughly `12.8s`.
- Two low-risk refactors did not materially improve the cold compile:
  - lazy-loading the image-analysis-only panels and renderer registration
  - moving page-level CopilotKit imports behind a lazy runtime bridge
- After those changes, the route still compiled at roughly `12.5s` to `13.2s`.
- Hot reload remained fast; the pain is the cold route compile path.

The dependency graph inspection also matters:

```bash
pnpm --dir ui why @copilotkit/react-ui @copilotkit/react-core streamdown mermaid lit rehype-raw
```

That showed `@copilotkit/react-core` / `@copilotkit/react-ui` pulling in:

- `streamdown`
- `mermaid`
- `rehype-raw`
- `lit`
- `@copilotkitnext/web-inspector`

The local compile logs also emitted the `Lit is in dev mode` warning during the cold route load.

## Current conclusion

The best current explanation is:

1. Next.js is not the main problem.
2. CopilotKit's client/UI dependency graph is the main problem.
3. Next.js is still carrying real architectural weight in this repo because it is hosting the UI-facing runtime and proxy routes.

That leads to a practical conclusion:

- If the goal is a faster local dev loop soon, the highest-leverage target is shrinking or replacing the `@copilotkit/react-ui` surface, especially `CopilotChat`.
- If the goal is a simpler long-term frontend stack, a move to plain React or Vite is plausible, but only if we also decide where the current Next route-handler work moves.

## Why this does not fully exonerate Next.js

Next.js still adds some framework complexity and some build/runtime overhead. It is just not the strongest suspect given the current evidence.

In this repo, the strongest reasons we still get value from Next are:

- file-based routing and navigation
- route handlers under `ui/src/app/api/**`
- same-origin hosting for the CopilotKit runtime endpoint
- dev rewrites for product images
- built-in font and metadata support in `ui/src/app/layout.tsx`

But the app is not getting much of the classic server-rendering upside because the current pages are heavily client-driven.

## Caveats

- A plain React or Vite move is not automatically a simplification if CopilotKit still drags large client-side dependencies into the bundle.
- CopilotKit's own issue tracker shows non-Next setups also having bundling and integration problems.
- This note captures the state of the codebase and issue tracker on 2026-03-20. It should be revisited after major CopilotKit upgrades or if the UI moves to a more headless custom integration.

## Links reviewed

### Framework docs

- Next.js Route Handlers: https://nextjs.org/docs/app/getting-started/route-handlers
- Next.js Server and Client Components: https://nextjs.org/docs/app/getting-started/server-and-client-components
- Next.js Linking and Navigating: https://nextjs.org/docs/app/getting-started/linking-and-navigating
- Next.js rewrites config: https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites
- React, "Start a New React Project": https://react.dev/learn/start-a-new-react-project
- Vite, "Why Vite": https://vite.dev/guide/why

### CopilotKit issue tracker searches

- Slow/performance search: https://github.com/CopilotKit/CopilotKit/issues?q=is%3Aissue+slow
- Headless search: https://github.com/CopilotKit/CopilotKit/issues?q=is%3Aissue+headless

### CopilotKit issues and PRs

- #3225 Built Bundle Size Explosion with CopilotKit v1.5+: https://github.com/CopilotKit/CopilotKit/issues/3225
- #3310 fix: remove server-side runtime dependency from runtime-client-gql: https://github.com/CopilotKit/CopilotKit/pull/3310
- #2731 Browser Build Fails Due to Accidental Inclusion of AWS SDK: https://github.com/CopilotKit/CopilotKit/issues/2731
- #2340 `<CopilotKit>` components requires to stay in index.tsx, causing implementation issues when not using NextJS: https://github.com/CopilotKit/CopilotKit/issues/2340
- #1863 remotrUrl not able to connect to remote endpoint /runtime/ written in python: https://github.com/CopilotKit/CopilotKit/issues/1863
- #1482 Configurable Option to Exclude Full Chat History from Requests: https://github.com/CopilotKit/CopilotKit/issues/1482
- #3455 The message list takes a long time to load when loading historical threads: https://github.com/CopilotKit/CopilotKit/issues/3455
- #1483 CopilotKit Retains Old Messages When Switching to an Empty Thread: https://github.com/CopilotKit/CopilotKit/issues/1483
- #2624 CopilotKit v1.10.6 doesn't pass threadId to agent.run(): https://github.com/CopilotKit/CopilotKit/issues/2624
- #2411 Tools’ calls are not being streamed to the frontend in AG_UI FastAPI integration: https://github.com/CopilotKit/CopilotKit/issues/2411
- #2684 CopilotKit rejects valid AG-UI tool-call streams when nested text/tool events arrive out of order: https://github.com/CopilotKit/CopilotKit/issues/2684
- #2060 useCoAgentStateRender cannot wok in headlees UI: https://github.com/CopilotKit/CopilotKit/issues/2060
- #2160 unable to trigger useCopilotAction from Fully Headless UI: https://github.com/CopilotKit/CopilotKit/issues/2160
- #1872 React 19 - CopilotTextarea fails with wrap-your-app error: https://github.com/CopilotKit/CopilotKit/issues/1872

## Recommended next step

If we want to buy back iteration speed without a larger migration, the next spike should be:

1. Replace `CopilotChat` on the agent route with a slimmer custom transcript/composer built on the lighter CopilotKit hooks.
2. Re-measure the cold compile path before spending time on a Next-to-Vite migration.

If that fails to move the number meaningfully, then a broader frontend-stack simplification becomes much easier to justify.
