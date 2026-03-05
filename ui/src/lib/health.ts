type HealthResponse = {
  status: string;
};

export async function getHealthStatus(): Promise<HealthResponse> {
  const response = await fetch("http://localhost/api/health");
  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
