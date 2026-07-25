import { ApiClientError, fetchApi, getApiBaseUrl } from "@/lib/api/client";
import { healthSchema, type BackendHealth } from "@/lib/api/schemas";

export type { BackendHealth };

export type BackendHealthResult = {
  ok: boolean;
  message: string;
  data: BackendHealth | null;
};

export async function fetchBackendHealth(
  apiBaseUrl = getApiBaseUrl(),
): Promise<BackendHealthResult> {
  try {
    const data = await fetchApi("/api/health", healthSchema, apiBaseUrl);
    return {
      ok: data.status === "ok",
      message: `${data.service} responded successfully.`,
      data,
    };
  } catch (error) {
    if (error instanceof ApiClientError) {
      return {
        ok: false,
        message: error.message,
        data: null,
      };
    }

    return {
      ok: false,
      message: "Backend health endpoint is not reachable. Start FastAPI on port 8000.",
      data: null,
    };
  }
}
