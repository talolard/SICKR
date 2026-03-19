"use client";

const agentCapabilityLabels: Record<string, string> = {
  search: "Product discovery",
  floor_plan_intake: "Room planning",
  image_analysis: "Image review",
};

export function formatAgentName(name: string): string {
  return name
    .split(/[_-]+/u)
    .filter((segment) => segment.length > 0)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function describeAgentCapability(name: string): string {
  return agentCapabilityLabels[name] ?? "Specialized workflow";
}
