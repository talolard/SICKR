export type RewriteRule = {
  source: string;
  destination: string;
};

type BuildDevProductImageRewritesOptions = {
  nodeEnv: string | undefined;
  agUiUrl: string | undefined;
};

export function backendOriginFromAgUiUrl(agUiUrl: string | undefined): string | null {
  if (!agUiUrl) {
    return null;
  }

  try {
    return new URL("../", agUiUrl).origin;
  } catch {
    return null;
  }
}

export function buildDevProductImageRewrites({
  nodeEnv,
  agUiUrl,
}: BuildDevProductImageRewritesOptions): RewriteRule[] {
  if (nodeEnv !== "development") {
    return [];
  }

  const backendOrigin = backendOriginFromAgUiUrl(agUiUrl);
  if (backendOrigin === null) {
    return [];
  }

  return [
    {
      source: "/static/product-images/:path*",
      destination: `${backendOrigin}/static/product-images/:path*`,
    },
  ];
}
