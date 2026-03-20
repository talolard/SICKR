"use client";

import { describeAgentCapability, formatAgentName } from "@/lib/agentLabels";

export type WorkspaceRailIcon =
  | "camera"
  | "favorite"
  | "info"
  | "light"
  | "materials"
  | "payments";

export type WorkspaceRailItem = {
  label: string;
  icon: WorkspaceRailIcon;
};

export type WorkspacePresentation = {
  capabilityLabel: string;
  consultationDescription: string;
  consultationEyebrow: string;
  consultationModeLabel: string;
  consultationTitle: string;
  description: string;
  railDescription: string;
  railEyebrow: string;
  railItems: WorkspaceRailItem[];
  railTitle: string;
  stageDescription: string;
  stageEyebrow: string;
  stageStatus: string;
  stageTitle: string;
  title: string;
};

function fallbackDescription(agentName: string): string {
  switch (agentName) {
    case "search":
      return "Curate products that solve the room brief without losing the design mood.";
    case "floor_plan_intake":
      return "Collect room architecture and turn it into iterative floor-plan drafts.";
    case "image_analysis":
      return "Review uploaded room photos to surface constraints, mood, and styling signals.";
    default:
      return "Work with the agent in a focused design consultation.";
  }
}

export function resolveWorkspacePresentation(
  agentName: string,
  description?: string | null,
): WorkspacePresentation {
  const resolvedDescription = description?.trim() || fallbackDescription(agentName);

  switch (agentName) {
    case "search":
      return {
        capabilityLabel: describeAgentCapability(agentName),
        consultationDescription:
          "Keep follow-up questions, rationale, and longer product comparisons contained in this consultation rail.",
        consultationEyebrow: "Curated product guidance",
        consultationModeLabel: "Curator mode active",
        consultationTitle: "Design Consultation",
        description: resolvedDescription,
        railDescription:
          "Keep the room brief visible while the search agent narrows the shortlist.",
        railEyebrow: "Project specifications",
        railItems: [
          { label: "Room Facts", icon: "info" },
          { label: "Preferences", icon: "favorite" },
          { label: "Budget", icon: "payments" },
          { label: "Materials", icon: "materials" },
        ],
        railTitle: "Project Specifications",
        stageDescription:
          "Bundle proposals and product groupings should stay readable, curated, and easy to compare.",
        stageEyebrow: "Curated results",
        stageStatus: "Shortlist live",
        stageTitle: "Bundle board",
        title: "Search",
      };
    case "floor_plan_intake":
      return {
        capabilityLabel: describeAgentCapability(agentName),
        consultationDescription:
          "Use the consultation rail for layout changes, clearance questions, and alternate room variants.",
        consultationEyebrow: "Refining your vision",
        consultationModeLabel: "Architectural mode active",
        consultationTitle: "Design Consultation",
        description: resolvedDescription,
        railDescription:
          "Keep the spatial brief and constraints visible while the layout evolves.",
        railEyebrow: "Project specifications",
        railItems: [
          { label: "Dimensions & Scale", icon: "info" },
          { label: "Layout Goals", icon: "favorite" },
          { label: "Budget", icon: "payments" },
          { label: "Materials", icon: "materials" },
        ],
        railTitle: "Room Specifications",
        stageDescription:
          "Render, review, and compare layout revisions without losing the drafting context.",
        stageEyebrow: "Architectural workbench",
        stageStatus: "Draft mode",
        stageTitle: "Drafting board",
        title: "Floor Plan Intake",
      };
    case "image_analysis":
      return {
        capabilityLabel: describeAgentCapability(agentName),
        consultationDescription:
          "Use the consultation rail to interpret the room photos and ask what to adjust next.",
        consultationEyebrow: "Reading the room",
        consultationModeLabel: "Image review active",
        consultationTitle: "Design Consultation",
        description: resolvedDescription,
        railDescription:
          "Capture what the room is already communicating before you move toward recommendations.",
        railEyebrow: "Photo context",
        railItems: [
          { label: "Room Facts", icon: "info" },
          { label: "Focal Points", icon: "camera" },
          { label: "Problem Areas", icon: "light" },
          { label: "Mood", icon: "favorite" },
        ],
        railTitle: "Visual Brief",
        stageDescription:
          "Collect images, compare angles, and keep the room context visible while the agent analyzes them.",
        stageEyebrow: "Image review",
        stageStatus: "Photo board ready",
        stageTitle: "Room photo board",
        title: "Image Analysis",
      };
    default:
      return {
        capabilityLabel: describeAgentCapability(agentName),
        consultationDescription:
          "Keep follow-up questions and long-form reasoning in this consultation rail.",
        consultationEyebrow: "Active consultation",
        consultationModeLabel: "Consultation active",
        consultationTitle: "Design Consultation",
        description: resolvedDescription,
        railDescription:
          "Keep the working brief visible while the agent builds toward the next recommendation.",
        railEyebrow: "Project specifications",
        railItems: [
          { label: "Context", icon: "info" },
          { label: "Preferences", icon: "favorite" },
          { label: "Budget", icon: "payments" },
          { label: "Materials", icon: "materials" },
        ],
        railTitle: "Project Specifications",
        stageDescription: "Keep the primary work surface central and the next action obvious.",
        stageEyebrow: "Workspace",
        stageStatus: "In progress",
        stageTitle: `${formatAgentName(agentName)} workspace`,
        title: formatAgentName(agentName),
      };
  }
}
