type HealthResponse = {
  status: string;
};

function healthUrl(): string {
  const origin = globalThis.location?.origin ?? "http://localhost";
  return new URL("/api/health", origin).toString();
}

export async function getHealthStatus(): Promise<HealthResponse> {
  const response = await fetch(healthUrl(), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
