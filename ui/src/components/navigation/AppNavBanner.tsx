"use client";

import { useRouter } from "next/navigation";

import type { SubagentItem } from "@/lib/subagents";

type AppNavBannerProps = {
  currentSubagentName: string | null;
  subagents: SubagentItem[];
};

export function AppNavBanner({
  currentSubagentName,
  subagents,
}: AppNavBannerProps): React.ReactElement {
  const router = useRouter();
  const selectedValue = currentSubagentName ?? "__home__";

  return (
    <header className="border-b border-gray-300 bg-gray-50 px-4 py-3">
      <div className="mx-auto flex w-full max-w-[1700px] items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 hover:bg-gray-100"
            onClick={() => router.push("/")}
            type="button"
          >
            Home
          </button>
          <div>
            <div className="text-sm text-gray-600">IKEA Agent Workspace</div>
            <h1 className="text-base font-semibold text-gray-900">
              {currentSubagentName ? `Subagent: ${currentSubagentName}` : "Main agent"}
            </h1>
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <span>My subagents</span>
          <select
            className="rounded border border-gray-400 bg-white px-2 py-1"
            onChange={(event) => {
              const next = event.target.value;
              if (next === "__home__") {
                router.push("/");
                return;
              }
              router.push(`/subagents/${next}`);
            }}
            value={selectedValue}
          >
            <option value="__home__">Home</option>
            {subagents.map((subagent) => (
              <option key={subagent.name} value={subagent.name}>
                {subagent.name}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}
