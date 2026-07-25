import { z } from "zod";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

type QueryValue = boolean | number | string | null | undefined;

export class ApiClientError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export function toQueryString(params: Record<string, QueryValue>): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function fetchApi<T>(
  path: string,
  schema: z.ZodType<T>,
  apiBaseUrl = getApiBaseUrl(),
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiClientError(await getErrorMessage(response), response.status);
  }

  const payload: unknown = await response.json();
  return schema.parse(payload);
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      error?: { message?: string };
      detail?: string;
    };
    return (
      payload.error?.message ?? payload.detail ?? `Request failed with HTTP ${response.status}.`
    );
  } catch {
    return `Request failed with HTTP ${response.status}.`;
  }
}
