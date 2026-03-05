"use client";

import type { ReactElement, ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core";

type CopilotKitProvidersProps = {
  children: ReactNode;
};

export function CopilotKitProviders({
  children,
}: CopilotKitProvidersProps): ReactElement {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="ikea_agent">
      {children}
    </CopilotKit>
  );
}

