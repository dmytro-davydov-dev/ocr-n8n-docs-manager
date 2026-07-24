import { ApiClient } from "@contract-review/api-client";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export const api = new ApiClient(baseUrl);
