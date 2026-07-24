export interface HealthResponse {
  status: string;
}

export class ApiClient {
  constructor(private readonly baseUrl: string) {}

  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }

    return (await response.json()) as HealthResponse;
  }
}
