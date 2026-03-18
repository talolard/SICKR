import type { NextConfig } from "next";

import { buildDevProductImageRewrites } from "./src/lib/devProductImageProxy";

const nextConfig: NextConfig = {
  async rewrites() {
    return buildDevProductImageRewrites({
      nodeEnv: process.env.NODE_ENV,
      agUiUrl: process.env.PY_AG_UI_URL,
    });
  },
};

export default nextConfig;
