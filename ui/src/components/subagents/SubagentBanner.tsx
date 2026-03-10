"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

import type { SubagentItem } from "@/lib/subagents";

type SubagentBannerProps = {
  currentSubagentName: string;
  subagents: SubagentItem[];
};

export function SubagentBanner({
  currentSubagentName,
  subagents,
}: SubagentBannerProps): React.ReactElement {
  const router = useRouter();
  const selectedName = useMemo(() => {
    return subagents.some((subagent) => subagent.name === currentSubagentName)
      ? currentSubagentName
      : "";
  }, [currentSubagentName, subagents]);

  return (
    <header className="border-b border-gray-300 bg-gray-50 px-4 py-3">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <div>
          <div className="text-sm text-gray-600">PydanticAI Subagent Chat</div>
          <h1 className="text-lg font-semibold text-gray-900">
            {selectedName.length > 0 ? selectedName : "Select a subagent"}
          </h1>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <span>Switch subagent</span>
          <select
            className="rounded border border-gray-400 bg-white px-2 py-1"
            value={selectedName}
            onChange={(event) => {
              const nextName = event.target.value;
              if (!nextName) {
                router.push("/subagents");
                return;
              }
              router.push(`/subagents/${nextName}`);
            }}
          >
            <option value="">Select</option>
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
